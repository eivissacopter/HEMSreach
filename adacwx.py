import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import requests
import math
from datetime import datetime, timedelta
from database import helicopter_bases, airports
from performance import H145D2_PERFORMANCE
import folium
from streamlit_folium import folium_static
import pytz
import pytaf

###########################################################################################

# Set the page configuration for wide mode and dark theme
st.set_page_config(layout="wide")

# Custom CSS to make the map full-screen and as the background, and to engage dark mode
st.markdown(
    """
    <style>
    body {
        background-color: #2e2e2e;
        color: white;
    }
    .reportview-container .main .block-container {
        padding: 0;
    }
    .reportview-container .main {
        background: none;
        padding: 0;
    }
    .sidebar .sidebar-content {
        background-color: #3e3e3e;
    }
    .fullScreenMap {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
    }
    .stSlider, .stNumberInput, .stTextInput {
        color: black;
    }
    .stNumberInput, .stTextInput {
        display: inline-block;
        margin-right: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

###########################################################################################

# Auto-refresh every 30 minutes (1800 seconds)
st_autorefresh(interval=1800 * 1000, key="data_refresh")

AVWX_API_KEY = '6za8qC9A_ccwpCc_lus3atiuA7f3c4mwQKMGzW1RVvY'

###########################################################################################

# Function to calculate distance and bearing between two points using the Haversine formula
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Earth radius in kilometers
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 0.539957  # Convert to nautical miles

    # Bearing calculation
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360  # Normalize to 0-360 degrees

    return distance, bearing

###########################################################################################

# Function to get reachable airports within a certain radius
@st.cache_data
def get_reachable_airports(base_lat, base_lon, total_flight_time_hours, climb_time_hours, descent_time_hours, cruise_speed_kt, wind_speed, wind_direction):
    reachable_airports = []
    cruise_time_hours = total_flight_time_hours - climb_time_hours - descent_time_hours
    for airport in airports:
        distance, bearing = haversine(base_lon, base_lat, airport['lon'], airport['lat'])
        ground_speed_kt = calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, bearing)
        if ground_speed_kt <= 0:
            continue
        time_to_airport_hours = distance / ground_speed_kt
        if time_to_airport_hours <= cruise_time_hours:
            reachable_airports.append((airport, distance, bearing, ground_speed_kt, time_to_airport_hours))
    reachable_airports.sort(key=lambda x: x[1])
    return reachable_airports

# Function to calculate ground speed considering wind
def calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, flight_direction):
    relative_wind_direction = math.radians(flight_direction - wind_direction)
    wind_component = wind_speed * math.cos(relative_wind_direction)
    ground_speed = cruise_speed_kt - wind_component  # Correct calculation to subtract wind impact for headwind
    return ground_speed

###########################################################################################

# Function to fetch METAR and TAF data from AVWX
@st.cache_data
def fetch_metar_taf_data(icao, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    metar_url = f"https://avwx.rest/api/metar/{icao}?options=summary"
    taf_url = f"https://avwx.rest/api/taf/{icao}?options=summary"

    try:
        response_metar = requests.get(metar_url, headers=headers)
        response_metar.raise_for_status()  # Raise an HTTPError for bad responses
        metar_data = response_metar.json()
    except requests.exceptions.RequestException as e:
        metar_data = f"Error fetching METAR data: {e}"

    try:
        response_taf = requests.get(taf_url, headers=headers)
        response_taf.raise_for_status()  # Raise an HTTPError for bad responses
        taf_data = response_taf.json()
    except requests.exceptions.RequestException as e:
        taf_data = f"Error fetching TAF data: {e}"

    return metar_data, taf_data

# Function to parse and interpret METAR data
def parse_metar(metar_raw):
    try:
        metar = pytaf.TAF(metar_raw)
        decoder = pytaf.Decoder(metar)
        return decoder.decode_taf()
    except Exception as e:
        st.error(f"Error decoding METAR: {e}")
        return None

def parse_taf(taf_raw):
    try:
        taf = pytaf.TAF(taf_raw)
        decoder = pytaf.Decoder(taf)
        return decoder.decode_taf()
    except Exception as e:
        st.error(f"Error decoding TAF: {e}")
        return None

###########################################################################################

# Sidebar for base selection and radius filter
with st.sidebar:
    base_names = [base['name'] for base in helicopter_bases]
    default_base = next(base for base in helicopter_bases if base['name'] == 'Christoph 77 Mainz')
    selected_base_name = st.selectbox('Select Home Base', base_names, index=base_names.index(default_base['name']))
    selected_base = next(base for base in helicopter_bases if base['name'] == selected_base_name)

    st.markdown("")
    cruise_altitude_ft = st.slider(
        'Cruise Altitude',
        min_value=3000, max_value=10000, value=5000, step=1000,
        format="%d ft"
    )
    total_fuel_kg = st.slider(
        'Total Fuel Upload',
        min_value=400, max_value=723, value=500, step=50,
        format="%d kg"
    )

    # Alternate required checkbox and input
    alternate_required = st.checkbox("Alternate Required")
    alternate_fuel = st.number_input("Alternate Fuel (kg)", value=0, step=10) if alternate_required else 0

    # Expandable section for fuel breakdown
    with st.expander("Fuel Policy"):
        system_test_and_air_taxi = 37
        holding_final_reserve = 100
        air_taxi_to_parking = 20
        contingency_fuel = 0.1 * (total_fuel_kg - holding_final_reserve - system_test_and_air_taxi - air_taxi_to_parking)
        trip_fuel_kg = total_fuel_kg - (system_test_and_air_taxi + holding_final_reserve + air_taxi_to_parking + contingency_fuel)

        # 15 minutes fuel calculation if alternate is not required
        if not alternate_required:
            fifteen_min_fuel = H145D2_PERFORMANCE['cruise']['fuel_burn_kgph'] * 0.25
            trip_fuel_kg -= fifteen_min_fuel
            approach_fuel = 30
        else:
            fifteen_min_fuel = 0
            approach_fuel = 60

        trip_fuel_kg -= (alternate_fuel + approach_fuel)

        fuel_data = {
            "Fuel Policy": ["System Test / Air Taxi", "Trip Fuel", "Final Reserve", "15 Minutes Fuel" if not alternate_required else "Alternate Fuel", "Approach Fuel", "Air Taxi to Parking", "Contingency Fuel"],
            "Fuel (kg)": [system_test_and_air_taxi, round(trip_fuel_kg), holding_final_reserve, round(fifteen_min_fuel) if not alternate_required else round(alternate_fuel), approach_fuel, air_taxi_to_parking, round(contingency_fuel)]
        }

        df_fuel = pd.DataFrame(fuel_data)
        st.table(df_fuel)

    # Input fields for wind direction and wind speed
    with st.expander("Wind Conditions"):
        col1, col2 = st.columns(2)
        with col1:
            wind_direction = st.number_input("Wind Direction (°)", value=0, step=1)
        with col2:
            wind_speed = st.number_input("Wind Speed (kt)", value=0, step=1)

###########################################################################################

from performance import H145D2_PERFORMANCE  # Import performance data

# Ensure H145D2_PERFORMANCE keys exist before accessing them
climb_performance = H145D2_PERFORMANCE.get('climb', {})
cruise_performance = H145D2_PERFORMANCE.get('cruise', {})
descend_performance = H145D2_PERFORMANCE.get('descend', {})

# Calculate mission radius with climb, cruise, and descent performance
climb_rate_fpm = climb_performance.get('climb_rate_fpm')
descent_rate_fpm = descend_performance.get('descend_rate_fpm')

climb_time_hours = (cruise_altitude_ft - 500) / climb_rate_fpm / 60
descent_time_hours = (cruise_altitude_ft - 500) / descent_rate_fpm / 60

climb_fuel_burn = climb_time_hours * climb_performance.get('fuel_burn_kgph')
descent_fuel_burn = descent_time_hours * descend_performance.get('fuel_burn_kgph')

cruise_fuel_burn_rate = cruise_performance.get('fuel_burn_kgph')
remaining_trip_fuel_kg = trip_fuel_kg - (climb_fuel_burn + descent_fuel_burn)
cruise_time_hours = remaining_trip_fuel_kg / cruise_fuel_burn_rate

total_flight_time_hours = climb_time_hours + cruise_time_hours + descent_time_hours

###########################################################################################

# Get reachable airports
reachable_airports = get_reachable_airports(selected_base['lat'], selected_base['lon'], total_flight_time_hours, climb_time_hours, descent_time_hours, cruise_performance.get('speed_kt', 115), wind_speed, wind_direction)

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

# Add reachable airports to map
reachable_airports_data = []
for airport, distance, bearing, ground_speed_kt, time_to_airport_hours in reachable_airports:
    metar_data, taf_data = fetch_metar_taf_data(airport['icao'], AVWX_API_KEY)
    
    if isinstance(metar_data, dict) and isinstance(taf_data, dict):
        metar_raw = metar_data.get('raw', '')
        taf_raw = taf_data.get('raw', '')
        metar_report = parse_metar(metar_raw)
        taf_report = parse_taf(taf_raw)

        fuel_required = time_to_airport_hours * cruise_fuel_burn_rate

        reachable_airports_data.append({
            "Airport": f"{airport['name']} ({airport['icao']})",
            "METAR": metar_report,
            "TAF": taf_report,
            "Distance (NM)": round(distance, 2),
            "Time (hours)": round(time_to_airport_hours, 2),
            "Track (°)": round(bearing, 2),
            "Ground Speed (kt)": round(ground_speed_kt, 2),
            "Fuel Required (kg)": round(fuel_required, 2)
        })
        
        weather_info = f"METAR: {metar_report}\\nTAF: {taf_report}"
        popup_text = f"{airport['name']} ({airport['icao']})"
        folium.Marker(
            location=[airport['lat'], airport['lon']],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="plane"),
        ).add_to(m)

###########################################################################################

# Display map
folium_static(m, width=1440, height=720)

# Ensure the columns exist before trying to highlight
if reachable_airports_data:
    df_reachable_airports = pd.DataFrame(reachable_airports_data)

    # Display the table with additional data
    st.markdown(df_reachable_airports.to_html(escape=False), unsafe_allow_html=True)
else:
    df_reachable_airports = pd.DataFrame(columns=["Airport", "METAR", "TAF", "Distance (NM)", "Time (hours)", "Track (°)", "Ground Speed (kt)", "Fuel Required (kg)"])

    # Display the table
    st.table(df_reachable_airports)

