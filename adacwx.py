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
    auto_fetch = st.checkbox("Try to get weather values automatically via API", value=False)
    
    if auto_fetch:
        # Placeholder for API function to fetch weather data
        freezing_level = 0  # Replace with actual function call
        wind_speed = 0  # Replace with actual function call
        wind_direction = 0  # Replace with actual function call
        cloud_text = "Fetched from API"
    else:
        wind_direction = st.text_input("Wind Direction (°)", "360")
        wind_speed = st.text_input("Wind Speed (kt)", "0")
        freezing_level = st.text_input("Freezing Level (ft)", "0")
        cloud_text = "Manual Input"
    
    st.markdown(f"**Wind at {cruise_altitude_ft} ft:** {wind_direction}°/{wind_speed} kt")
    st.markdown(f"**Freezing Level (Altitude):** {freezing_level} ft")
    st.markdown(f"**Clouds:** {cloud_text}")

# Calculate mission radius
cruise_speed_kt = H145D2_PERFORMANCE['cruise_speed_kt']
fuel_burn_kgph = H145D2_PERFORMANCE['fuel_burn_kgph']
flight_time_hours = fuel_kg / fuel_burn_kgph

# Calculate ground speed considering wind
if isinstance(wind_direction, str) and wind_direction.isnumeric():
    wind_direction = int(wind_direction)
if isinstance(wind_speed, str) and wind_speed.isnumeric():
    wind_speed = int(wind_speed)

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
    
    if not auto_fetch:
        wind_direction = st.text_input(f"Wind Direction (°) at {airport['icao']}", "360")
        wind_speed = st.text_input(f"Wind Speed (kt) at {airport['icao']}", "0")
        freezing_level = st.text_input(f"Freezing Level (ft) at {airport['icao']}", "0")
        cloud_text = "Manual Input"
    else:
        # Placeholder for API function to fetch weather data
        freezing_level = 0  # Replace with actual function call
        wind_speed = 0  # Replace with actual function call
        wind_direction = 0  # Replace with actual function call
        cloud_text = "Fetched from API"
    
    if freezing_level is not None and wind_speed is not None and wind_direction is not None:
        popup_text = (
            f"{airport['name']} ({airport['icao']}) - {distance:.1f} NM\n"
            f"Freezing Level: {freezing_level} ft\n"
            f"Wind: {wind_direction}°/{wind_speed} kt\n"
            f"Clouds: {cloud_text}"
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
