import streamlit as st
import pandas as pd
import requests
import math

# Sample data: List of rescue helicopter bases (should be replaced with actual data)
bases = [
    {'name': 'Christoph 77 Mainz', 'lat': 49.992, 'lon': 8.247},
    {'name': 'Christoph 18 Ochsenfurt', 'lat': 49.662, 'lon': 10.052}
]

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

# Placeholder function to get airports within a certain radius (should be replaced with actual data retrieval)
def get_airports_within_radius(base_lat, base_lon, radius_nm):
    # This is a placeholder list of airports with instrument approaches
    airports = [
        {'name': 'Frankfurt Airport', 'icao': 'EDDF', 'lat': 50.037, 'lon': 8.562},
        {'name': 'Munich Airport', 'icao': 'EDDM', 'lat': 48.353, 'lon': 11.786},
        # Add more airports as needed
    ]
    
    nearby_airports = [airport for airport in airports if haversine(base_lon, base_lat, airport['lon'], airport['lat']) <= radius_nm]
    return nearby_airports

# Function to fetch METAR and TAF data
def fetch_weather(icao_code):
    metar_url = f'https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao_code}.TXT'
    taf_url = f'https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{icao_code}.TXT'
    
    metar = requests.get(metar_url).text.split('\n')[1] if requests.get(metar_url).status_code == 200 else "No data"
    taf = requests.get(taf_url).text.split('\n')[1] if requests.get(taf_url).status_code == 200 else "No data"
    
    return metar, taf

# Function to check weather criteria
def check_weather_criteria(metar, taf):
    # Placeholder logic to check weather criteria
    # In practice, you would parse the METAR/TAF strings and apply your criteria
    visibility_ok = '3000' in metar or '3000' in taf
    ceiling_ok = '700' in metar or '700' in taf
    return visibility_ok and ceiling_ok

# Streamlit app layout
st.title('Aviation Weather Checker')

# Select base
base_names = [base['name'] for base in bases]
selected_base_name = st.selectbox('Select Home Base', base_names)
selected_base = next(base for base in bases if base['name'] == selected_base_name)

# Get airports within radius
radius_nm = 250
nearby_airports = get_airports_within_radius(selected_base['lat'], selected_base['lon'], radius_nm)

# Display nearby airports and check weather
st.subheader(f'Airports within {radius_nm} NM of {selected_base_name}')
for airport in nearby_airports:
    metar, taf = fetch_weather(airport['icao'])
    weather_ok = check_weather_criteria(metar, taf)
    
    st.markdown(f"### {airport['name']} ({airport['icao']})")
    st.text(f"METAR: {metar}")
    st.text(f"TAF: {taf}")
    
    if weather_ok:
        st.success("IFR OK")
    else:
        st.error("IFR Not OK")
