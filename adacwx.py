import streamlit as st
import pandas as pd
import requests
import math
import re
from datetime import datetime, timedelta
from database import helicopter_bases, airports
import folium
from streamlit_folium import folium_static
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import numpy as np
import pytesseract
import openmeteo_requests
import requests_cache
from retry_requests import retry
import geopandas as gpd
from requests.exceptions import HTTPError

# Set the page configuration at the very top
st.set_page_config(layout="wide")

# Custom CSS to make the map full-screen and as the background
st.markdown(
    """
    <style>
    .reportview-container .main .block-container {
        padding: 0;
    }
    .reportview-container .main {
        background: none;
        padding: 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .fullScreenMap {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Function to calculate distance between two points using the Haversine formula
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Earth radius in kilometers
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 0.539957  # Convert to nautical miles
    return distance

# Function to get airports within a certain radius
def get_airports_within_radius(base_lat, base_lon, radius_nm):
    nearby_airports = []
    for airport in airports:
        distance = haversine(base_lon, base_lat, airport['lon'], airport['lat'])
        if distance <= radius_nm:
            nearby_airports.append((airport, distance))
    # Sort airports by distance
    nearby_airports.sort(key=lambda x: x[1])
    return nearby_airports

# Function to fetch METAR and TAF data
def fetch_weather(icao_code):
    metar_url = f'https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao_code}.TXT'
    taf_url = f'https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{icao_code}.TXT'
    
    metar_response = requests.get(metar_url)
    taf_response = requests.get(taf_url)
    
    metar = metar_response.text.split('\n')[1] if metar_response.status_code == 200 and len(metar_response.text.split('\n')) > 1 else "No data"
    taf = taf_response.text if taf_response.status_code == 200 else "No data"
    
    return metar, taf

# Function to parse METAR visibility and cloud base
def parse_metar(metar):
    try:
        visibility_match = re.search(r'\s(\d{4})\s', metar)
        visibility = int(visibility_match.group(1)) if visibility_match else None
        
        cloud_base_match = re.search(r'\s(BKN|FEW|SCT|OVC)(\d{3})\s', metar)
        cloud_base = int(cloud_base_match.group(2)) * 100 if cloud_base_match else None
        
        return visibility, cloud_base
    except Exception as e:
        st.error(f"Error parsing METAR: {e}")
        return None, None

# Function to parse TAF visibility and cloud base
def parse_taf(taf):
    try:
        forecast_blocks = taf.split(" FM")
        forecasts = []
        now = datetime.utcnow()
        
        for block in forecast_blocks[1:]:
            time_match = re.match(r'(\d{2})(\d{2})/(\d{2})(\d{2})', block)
            if time_match:
                start_hour = int(time_match.group(1))
                start_minute = int(time_match.group(2))
                start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                visibility_match = re.search(r'\s(\d{4})\s', block)
                visibility = int(visibility_match.group(1)) if visibility_match else None
                
                cloud_base_match = re.search(r'\s(BKN|FEW|SCT|OVC)(\d{3})\s', block)
                cloud_base = int(cloud_base_match.group(2)) * 100 if cloud_base_match else None
                
                forecasts.append((start_time, visibility, cloud_base))
        
        return forecasts
    except Exception as e:
        st.error(f"Error parsing TAF: {e}")
        return []

# Function to check weather criteria
def check_weather_criteria(metar, taf):
    try:
        visibility_ok, ceiling_ok = True, True
        metar_visibility, metar_ceiling = parse_metar(metar)
        
        if metar_visibility is not None:
            visibility_ok = metar_visibility >= 3000
        
        if metar_ceiling is not None:
            ceiling_ok = metar_ceiling >= 700
        
        forecasts = parse_taf(taf)
        now = datetime.utcnow()
        future_time = now + timedelta(hours=5)
        
        for forecast_time, forecast_visibility, forecast_ceiling in forecasts:
            if forecast_time > future_time:
                break
            if forecast_visibility is not None:
                visibility_ok = visibility_ok and (forecast_visibility >= 3000)
            if forecast_ceiling is not None:
                ceiling_ok = ceiling_ok and (forecast_ceiling >= 700)
        
        return visibility_ok and ceiling_ok
    except Exception as e:
        st.error(f"Error checking weather criteria: {e}")
        return False

# Function to fetch freezing level and wind data using OpenMeteo API
@st.cache_data
def fetch_freezing_level_and_wind(lat, lon, altitude_ft):
    altitude_m = round(altitude_ft * 0.3048)  # Convert feet to meters and round
    altitude_levels = [1500, 3000, 5000]  # Supported altitude levels in meters for wind
    altitude_m = min(altitude_levels, key=lambda x: abs(x - altitude_m))  # Find the closest supported level
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "freezing_level_height,wind_speed_10m,wind_direction_10m",
        "start": datetime.utcnow().isoformat(),
        "end": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        hourly = data['hourly']
        freezing_level = hourly['freezing_level_height'][0]  # Use the first value for now
        wind_speed = hourly['wind_speed_10m'][0]  # Use the first value for now
        wind_direction = hourly['wind_direction_10m'][0]  # Use the first value for now
    except Exception as e:
        st.error(f"Error fetching data from OpenMeteo API: {e}")
        return None, None, None

    return freezing_level, wind_speed, wind_direction

# Function to extract MVA data from an image URL using OCR
def extract_mva_data_from_image_url(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    # Convert image to grayscale
    gray = img.convert('L')
    # Enhance image
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2)
    # Apply thresholding
    bw = gray.point(lambda x: 0 if x < 128 else 255, '1')

    mva_data = []
    width, height = bw.size

    # OCR processing
    data = pytesseract.image_to_data(bw, output_type=pytesseract.Output.DICT)
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        if int(data['conf'][i]) > 60:  # Confidence threshold
            text = data['text'][i]
            try:
                mva_value = int(re.search(r'\d+', text).group())
                x, y, w, h = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                polygon = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                mva_data.append({
                    'polygon': polygon,
                    'mva': mva_value
                })
            except (ValueError, AttributeError):
                continue

    return mva_data

# Function to fetch DFS geo layers using WFS
@st.cache_data
def fetch_dfs_geo_layers():
    url = "https://haleconnect.com/ows/services/org.732.341f2791-919e-49de-8d86-3b18e040c430_wfs?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0"
    try:
        response = requests.get(url)
        response.raise_for_status()
        gdf = gpd.read_file(response.content)
    except HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        st.error(f"Other error occurred: {err}")
        return None

    return gdf

# Sidebar for base selection and radius filter
with st.sidebar:
    base_names = [base['name'] for base in helicopter_bases]
    default_base = next(base for base in helicopter_bases if base['name'] == 'Christoph 77 Mainz')
    selected_base_name = st.selectbox('Select Home Base', base_names, index=base_names.index(default_base['name']))
    selected_base = next(base for base in helicopter_bases if base['name'] == selected_base_name)
    radius_nm = st.slider('Select radius in nautical miles', min_value=50, max_value=500, value=200, step=10)
    cruise_altitude_ft = st.slider('Select cruise altitude in feet', min_value=1000, max_value=10000, value=5000, step=500)

    # Add switches for layers
    show_geo_data = st.checkbox("Show Geo-Data from DFS")
    show_mva_layer = st.checkbox("Show Minimum Vectoring Altitudes (MVA)")
    show_freezing_level_layer = st.checkbox("Show Freezing Level Layer")

# Get airports within radius
nearby_airports = get_airports_within_radius(selected_base['lat'], selected_base['lon'], radius_nm)

# Create map centered on selected base
m = folium.Map(location=[selected_base['lat'], selected_base['lon']], zoom_start=7)

# Add selected base to map
folium.Marker(
    location=[selected_base['lat'], selected_base['lon']],
    popup=selected_base_name,
    icon=folium.Icon(color="blue", icon="info-sign"),
).add_to(m)

# Add airports to map
for airport, distance in nearby_airports:
    metar, taf = fetch_weather(airport['icao'])
    weather_ok = check_weather_criteria(metar, taf)
    
    color = "green" if weather_ok else "red"
    
    freezing_level, wind_speed, wind_direction = fetch_freezing_level_and_wind(airport['lat'], airport['lon'], cruise_altitude_ft)
    
    folium.Marker(
        location=[airport['lat'], airport['lon']],
        popup=f"{airport['name']} ({airport['icao']}) - {distance:.1f} NM\n"
              f"Freezing Level: {freezing_level:.0f} ft\n"
              f"Wind: {wind_speed} m/s from {wind_direction}°",
        icon=folium.Icon(color=color),
    ).add_to(m)

# Add Geo-Data from DFS
if show_geo_data:
    gdf = fetch_dfs_geo_layers()
    if gdf is not None:
        folium.GeoJson(gdf, name="Geo-Data from DFS").add_to(m)

# Add Minimum Vectoring Altitudes (MVA) layer
if show_mva_layer:
    image_url = "https://aip.dfs.de/BasicIFR/pages/P00DD0.html"  # URL to the image
    mva_data = extract_mva_data_from_image_url(image_url)
    for mva in mva_data:
        folium.Polygon(
            locations=[(point[0], point[1]) for point in mva['polygon']],
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.4,
            popup=f"MVA: {mva['mva']} ft"
        ).add_to(m)

# Display map
folium_static(m, width=1920, height=1080)
