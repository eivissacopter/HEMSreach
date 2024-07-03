import streamlit as st
import pandas as pd
import requests
import math
import re
from datetime import datetime, timedelta
from database import helicopter_bases, airports
from performance import H145D2_PERFORMANCE
import folium
from streamlit_folium import folium_static
import openmeteo_requests
import requests_cache
from retry_requests import retry

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
    .stSlider {
        height: 100%;
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

# Function to fetch freezing level, wind, cloud data, and thunderstorm forecast using OpenMeteo API
@st.cache_data
def fetch_freezing_level_and_wind(lat, lon, altitude_ft):
    altitude_m = round(altitude_ft * 0.3048)  # Convert feet to meters and round to the nearest meter
    altitude_levels = [1500, 3000, 5000]  # Supported altitude levels in meters for wind
    altitude_m = min(altitude_levels, key=lambda x: abs(x - altitude_m))  # Find the closest supported level
    
    url = "https://api.open-meteo.com/v1/dwd-icon"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": f"freezing_level_height,wind_speed_{altitude_m}m,wind_direction_{altitude_m}m,cloudcover,weather_code",
        "wind_speed_unit": "kn",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        hourly = data['hourly']
        freezing_level_height = hourly['freezing_level_height'][0]  # Use the first value for now
        wind_speed_knots = hourly[f'wind_speed_{altitude_m}m'][0]  # Use the first value for now
        wind_direction = hourly[f'wind_direction_{altitude_m}m'][0]  # Use the first value for now
        cloudcover = hourly['cloudcover'][0]  # Use the first value for now
        weather_code = hourly['weather_code'][0]  # Use the first value for now

        # Convert freezing level height from meters to feet
        freezing_level_altitude_ft = round(freezing_level_height * 3.28084)

        # Determine cloud conditions
        if cloudcover > 0:
            cloud_text = f"Clouds present"
        else:
            cloud_text = "Sky clear"

        # Determine thunderstorm conditions
        thunderstorm = "Yes" if weather_code in [95, 96, 99] else "No"

    except Exception as e:
        st.error(f"Error fetching data from OpenMeteo API: {e}")
        return None, None, None, None, None

    return freezing_level_altitude_ft, wind_speed_knots, wind_direction, cloud_text, thunderstorm

# Sidebar for base selection and radius filter
with st.sidebar:
    base_names = [base['name'] for base in helicopter_bases]
    default_base = next(base for base in helicopter_bases if base['name'] == 'Christoph 77 Mainz')
    selected_base_name = st.selectbox('Select Home Base', base_names, index=base_names.index(default_base['name']))
    selected_base = next(base for base in helicopter_bases if base['name'] == selected_base_name)
    
    st.markdown("### Flight Parameters")
    cruise_altitude_ft = st.slider(
        'Select cruise altitude in feet', 
        min_value=3000, max_value=10000, value=5000, step=1000,
        format="%d ft"
    )
    fuel_kg = st.slider(
        'Total Fuel Upload (kg)', 
        min_value=300, max_value=723, value=500, step=50,
        format="%d kg"
    )
    
    st.markdown("### Weather at Home Base")
    freezing_level, wind_speed, wind_direction, cloud_text, thunderstorm = fetch_freezing_level_and_wind(
        selected_base['lat'], selected_base['lon'], cruise_altitude_ft
    )
    
    st.markdown(f"**Wind at {cruise_altitude_ft} ft:** {wind_direction}°/{wind_speed} kt")
    st.markdown(f"**Freezing Level (Altitude):** {freezing_level} ft")
    st.markdown(f"**Clouds:** {cloud_text}")
    st.markdown(f"**Thunderstorm Forecast:** {thunderstorm}")


# Calculate mission radius
cruise_speed_kt = H145D2_PERFORMANCE['cruise_speed_kt']
fuel_burn_kgph = H145D2_PERFORMANCE['fuel_burn_kgph']
flight_time_hours = fuel_kg / fuel_burn_kgph

# Calculate ground speed considering wind
if wind_direction is not None:
    wind_component = wind_speed * math.cos(math.radians(wind_direction))
    ground_speed_kt = cruise_speed_kt + wind_component
else:
    ground_speed_kt = cruise_speed_kt

mission_radius_nm = ground_speed_kt * flight_time_hours

# Get airports within mission radius
nearby_airports = get_airports_within_radius(selected_base['lat'], selected_base['lon'], mission_radius_nm)

# Create map centered on selected base
m = folium.Map(location=[selected_base['lat'], selected_base['lon']], zoom_start=7)

# Add OpenFlightMap tiles
folium.TileLayer(
    tiles='https://{s}.tile.openflightmaps.org/{z}/{x}/{y}.png',
    attr='&copy; <a href="https://www.openflightmaps.org">OpenFlightMaps</a>',
    name='OpenFlightMaps'
).add_to(m)

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
    
    freezing_level, wind_speed, wind_direction, cloud_text, thunderstorm = fetch_freezing_level_and_wind(
        airport['lat'], airport['lon'], cruise_altitude_ft
    )
    
    if freezing_level is not None and wind_speed is not None and wind_direction is not None:
        popup_text = (
            f"{airport['name']} ({airport['icao']}) - {distance:.1f} NM\n"
            f"Freezing Level: {freezing_level} ft\n"
            f"Wind: {wind_direction}°/{wind_speed} kt\n"
            f"Clouds: {cloud_text}\n"
            f"Thunderstorm Forecast: {thunderstorm}"
        )
    else:
        popup_text = (
            f"{airport['name']} ({airport['icao']}) - {distance:.1f} NM\n"
            "Weather data not available"
        )

    folium.Marker(
        location=[airport['lat'], airport['lon']],
        popup=popup_text,
        icon=folium.Icon(color=color),
    ).add_to(m)

# Display map
folium_static(m, width=1920, height=1080)
