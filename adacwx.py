import streamlit as st
import pandas as pd
import requests
import math

# Helicopter bases data
helicopter_bases = [
    {"name": "Christoph 1 Munich", "lat": 48.3539, "lon": 11.7861},
    {"name": "Christoph 2 Frankfurt", "lat": 50.0333, "lon": 8.5706},
    {"name": "Christoph 3 Cologne", "lat": 50.8659, "lon": 7.1427},
    # Add all other ADAC Luftrettung helicopter bases here
]

# Airports with IFR approaches data
airports = [
    {"name": "Frankfurt Airport", "icao": "EDDF", "lat": 50.0379, "lon": 8.5622},
    {"name": "Munich Airport", "icao": "EDDM", "lat": 48.3538, "lon": 11.7861},
    {"name": "Berlin Brandenburg Airport", "icao": "EDDB", "lat": 52.3667, "lon": 13.5033},
    {"name": "Hamburg Airport", "icao": "EDDH", "lat": 53.6303, "lon": 9.9883},
    {"name": "Stuttgart Airport", "icao": "EDDS", "lat": 48.6899, "lon": 9.2219},
    # Add more airports with IFR approaches as needed
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

# Function to get airports within a certain radius
def get_airports_within_radius(base_lat, base_lon, radius_nm):
    nearby_airports = [airport for airport in airports if haversine(base_lon, base_lat, airport['lon'], airport['lat']) <= radius_nm]
    return nearby_airports

# Function to fetch METAR and TAF data
def fetch_weather(icao_code):
    metar_url = f'https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao_code}.TXT'
    taf_url = f'https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{icao_code}.TXT'
    
    metar_response = requests.get(metar_url)
    taf_response = requests.get(taf_url)
    
    metar = metar_response.text.split('\n')[1] if metar_response.status_code == 200 else "No data"
    taf = taf_response.text.split('\n')[1] if taf_response.status_code == 200 else "No data"
    
    return metar, taf

# Function to check weather criteria
def check_weather_criteria(metar, taf):
    visibility_ok = '3000' in metar or '3000' in taf
    ceiling_ok = '700' in metar or '700' in taf
    return visibility_ok and ceiling_ok

# Streamlit app layout
st.title('Aviation Weather Checker')

# Select base
base_names = [base['name'] for base in helicopter_bases]
selected_base_name = st.selectbox('Select Home Base', base_names)
selected_base = next(base for base in helicopter_bases if base['name'] == selected_base_name)

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
