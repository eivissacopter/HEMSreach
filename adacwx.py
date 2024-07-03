import streamlit as st
import pandas as pd
import requests
import math
from database import helicopter_bases, airports
from performance import H145D2_PERFORMANCE
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

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
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
    }
    .stSlider {
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

# Function to get reachable airports within a certain radius
def get_reachable_airports(base_lat, base_lon, flight_time_hours, cruise_speed_kt, wind_speed, wind_direction):
    reachable_airports = []
    for airport in airports:
        distance, bearing = haversine(base_lon, base_lat, airport['lon'], airport['lat'])
        ground_speed_kt = calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, bearing)
        if ground_speed_kt <= 0:
            continue
        time_to_airport_hours = distance / ground_speed_kt
        if time_to_airport_hours <= flight_time_hours:
            reachable_airports.append((airport, distance))
    reachable_airports.sort(key=lambda x: x[1])
    return reachable_airports

# Function to calculate ground speed considering wind
def calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, flight_direction):
    relative_wind_direction = math.radians(flight_direction - wind_direction)
    wind_component = wind_speed * math.cos(relative_wind_direction)
    ground_speed = cruise_speed_kt - wind_component  # Invert the calculation to correctly apply wind impact
    return ground_speed

# Function to fetch weather data for IFR classification
def fetch_weather_data(lat, lon, hours_ahead):
    end_time = datetime.utcnow() + timedelta(hours=hours_ahead)
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "visibility,cloudcover",
        "start": datetime.utcnow().isoformat() + "Z",
        "end": end_time.isoformat() + "Z",
    }
    response = requests.get(base_url, params=params)
    data = response.json()

    if "hourly" in data:
        visibility = data["hourly"]["visibility"]
        cloud_cover = data["hourly"]["cloudcover"]
    else:
        visibility = []
        cloud_cover = []

    return visibility, cloud_cover

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
    total_fuel_kg = st.slider(
        'Total Fuel Upload (kg)', 
        min_value=300, max_value=723, value=500, step=50,
        format="%d kg"
    )

    # Alternate required checkbox and input
    alternate_required = st.checkbox("Alternate Required")
    alternate_fuel = st.number_input("Alternate Fuel (kg)", value=0, step=10) if alternate_required else 0

    # Expandable section for fuel breakdown
    with st.expander("Show Fuel Breakdown"):
        system_test_and_air_taxi = 37
        holding_final_reserve = 100
        air_taxi_to_parking = 20

        contingency_fuel = 0.1 * (total_fuel_kg - holding_final_reserve - system_test_and_air_taxi - air_taxi_to_parking)
        trip_fuel_kg = total_fuel_kg - (system_test_and_air_taxi + holding_final_reserve + air_taxi_to_parking + contingency_fuel)

        # 15 minutes fuel calculation if alternate is not required
        if not alternate_required:
            fifteen_min_fuel = H145D2_PERFORMANCE['fuel_burn_kgph'] * 0.25
            trip_fuel_kg -= fifteen_min_fuel
            approach_fuel = 30
        else:
            fifteen_min_fuel = 0
            approach_fuel = 60

        trip_fuel_kg -= (alternate_fuel + approach_fuel)

        fuel_data = {
            "Fuel Component": ["System Test and Air Taxi", "Trip Fuel", "Holding/Final Reserve", "15 Minutes Fuel" if not alternate_required else "Alternate Fuel", "Approach Fuel", "Air Taxi to Parking", "Contingency Fuel"],
            "Fuel (kg)": [system_test_and_air_taxi, round(trip_fuel_kg), holding_final_reserve, round(fifteen_min_fuel) if not alternate_required else round(alternate_fuel), approach_fuel, air_taxi_to_parking, round(contingency_fuel)]
        }
        df_fuel = pd.DataFrame(fuel_data)
        st.table(df_fuel)

    # Expandable section for weather configuration
    with st.expander("Weather Config"):
        weather_time_window = st.slider('Weather Time Window (hours)', min_value=1, max_value=10, value=5, step=1)
        
        st.markdown("### NVFR Limits")
        nvfr_vis = st.text_input("NVFR Vis (m)", "5000")
        nvfr_ceiling = st.text_input("NVFR Ceiling (ft)", "1500")

        st.markdown("### DVFR Limits")
        dvfr_vis = st.text_input("DVFR Vis (m)", "3000")
        dvfr_ceiling = st.text_input("DVFR Ceiling (ft)", "500")

        st.markdown("### NO ALT Limits")
        no_alt_vis = st.text_input("NO ALT Vis (m)", "3000")
        no_alt_ceiling = st.text_input("NO ALT Ceiling (ft)", "700")

        st.markdown("### ALT OK Limits")
        alt_ok_vis = st.text_input("ALT OK Vis (m)", "900")
        alt_ok_ceiling = st.text_input("ALT OK Ceiling (ft)", "400")

        st.markdown("### DEST OK Limits")
        dest_ok_vis = st.text_input("DEST OK Vis (m)", "500")
        dest_ok_ceiling = st.text_input("DEST OK Ceiling (ft)", "200")

# Ensure all necessary variables are defined before use
fuel_burn_kgph = H145D2_PERFORMANCE['fuel_burn_kgph']
flight_time_hours = trip_fuel_kg / fuel_burn_kgph
cruise_speed_kt = H145D2_PERFORMANCE['cruise_speed_kt']

# Get reachable airports
reachable_airports = get_reachable_airports(selected_base['lat'], selected_base['lon'], flight_time_hours, cruise_speed_kt, wind_speed, wind_direction)

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
for airport, distance in reachable_airports:
    visibility, cloud_cover = fetch_weather_data(airport['lat'], airport['lon'], weather_time_window)
    
    if all(v >= float(dest_ok_vis) and c <= float(dest_ok_ceiling) for v, c in zip(visibility, cloud_cover)):
        status = "DEST OK"
        color = "green"
    elif all(v >= float(alt_ok_vis) and c <= float(alt_ok_ceiling) for v, c in zip(visibility, cloud_cover)):
        status = "ALT OK"
        color = "green"
    elif all(v >= float(no_alt_vis) and c <= float(no_alt_ceiling) for v, c in zip(visibility, cloud_cover)):
        status = "NO ALT"
        color = "yellow"
    elif all(v >= float(dvfr_vis) and c <= float(dvfr_ceiling) for v, c in zip(visibility, cloud_cover)):
        status = "DVFR"
        color = "orange"
    elif all(v >= float(nvfr_vis) and c <= float(nvfr_ceiling) for v, c in zip(visibility, cloud_cover)):
        status = "NVFR"
        color = "red"
    else:
        status = "UNKNOWN"
        color = "gray"

    popup_text = f"{airport['name']} ({airport['icao']}) - {distance:.1f} NM - {status}"
    folium.Marker(
        location=[airport['lat'], airport['lon']],
        popup=popup_text,
        icon=folium.Icon(color=color, icon="plane"),
    ).add_to(m)

# Display map
folium_static(m, width=1280, height=800)
