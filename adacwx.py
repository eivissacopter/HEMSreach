import streamlit as st
import pandas as pd
import requests
import math
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

# Function to fetch weather data from API
def fetch_weather_data(lat, lon, cruise_altitude_ft):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,cloudcover,windspeed_10m,winddirection_10m",
        "elevation": cruise_altitude_ft,
        "current_weather": True,
    }
    response = requests.get(base_url, params=params)
    data = response.json()

    if "current_weather" in data:
        current_weather = data["current_weather"]
        wind_speed = current_weather["windspeed"]
        wind_direction = current_weather["winddirection"]
        freezing_level = current_weather["elevation"]
        cloud_cover = data["hourly"]["cloudcover"][0] if data["hourly"]["cloudcover"] else "N/A"
        icing_warning = "Moderate" if cloud_cover > 50 else "Light"
    else:
        wind_speed = "N/A"
        wind_direction = "N/A"
        freezing_level = "N/A"
        icing_warning = "N/A"

    return wind_speed, wind_direction, freezing_level, icing_warning

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

    # Expandable section for fuel breakdown
    with st.expander("Show Fuel Breakdown"):
        system_test_and_air_taxi = 37
        holding_final_reserve = 100
        air_taxi_to_parking = 20

        contingency_fuel = 0.1 * (total_fuel_kg - holding_final_reserve - system_test_and_air_taxi - air_taxi_to_parking)
        trip_fuel_kg = total_fuel_kg - (system_test_and_air_taxi + holding_final_reserve + air_taxi_to_parking + contingency_fuel)

        # Number of approaches and approach fuel logic
        approach_fuel = 30
        if alternate_required:
            approach_fuel = 60
        trip_fuel_kg -= approach_fuel

        fuel_data = {
            "Fuel Component": ["System Test and Air Taxi", "Holding/Final Reserve", "Air Taxi to Parking", "Contingency Fuel", "Approach Fuel", "Trip Fuel"],
            "Fuel (kg)": [system_test_and_air_taxi, holding_final_reserve, air_taxi_to_parking, round(contingency_fuel), approach_fuel, round(trip_fuel_kg)]
        }
        df_fuel = pd.DataFrame(fuel_data)
        st.table(df_fuel)

    # Alternate required checkbox and input
    alternate_required = st.checkbox("Alternate Required")
    alternate_fuel = st.number_input("Alternate Fuel (kg)", value=0, step=10) if alternate_required else 0
    trip_fuel_kg -= alternate_fuel

    # Show calculated flight time below the fuel slider
    fuel_burn_kgph = H145D2_PERFORMANCE['fuel_burn_kgph']
    flight_time_hours = trip_fuel_kg / fuel_burn_kgph
    flight_time_minutes = int((flight_time_hours - int(flight_time_hours)) * 60)
    flight_time_display = f"{int(flight_time_hours)}h {flight_time_minutes}m"
    st.markdown(f"### Calculated Flight Time: {flight_time_display}")

    st.markdown("### Weather at Home Base")
    auto_fetch = st.checkbox("Try to get weather values automatically via API", value=False)
    
    if auto_fetch:
        wind_speed, wind_direction, freezing_level, icing_warning = fetch_weather_data(selected_base['lat'], selected_base['lon'], cruise_altitude_ft)
    else:
        wind_direction = st.text_input("Wind Direction (°)", "360")
        wind_speed = st.text_input("Wind Speed (kt)", "0")
        freezing_level = st.text_input("Freezing Level (ft)", "0")
        icing_warning = "Manual Input"

    st.markdown(f"**Wind at {cruise_altitude_ft} ft:** {wind_direction}°/{wind_speed} kt")
    st.markdown(f"**Freezing Level (Altitude):** {freezing_level} ft")
    st.markdown(f"**Expected Icing:** {icing_warning}")

    # Manual input for Minimum Vectoring Altitude
    min_vectoring_altitude = st.text_input("Minimum Vectoring Altitude below Freezing Level (ft)")

# Calculate mission radius
cruise_speed_kt = H145D2_PERFORMANCE['cruise_speed_kt']

# Get reachable airports
reachable_airports = get_reachable_airports(selected_base['lat'], selected_base['lon'], flight_time_hours, cruise_speed_kt, float(wind_speed), float(wind_direction))

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
    color = "green"
    popup_text = f"{airport['name']} ({airport['icao']}) - {distance:.1f} NM"
    folium.Marker(
        location=[airport['lat'], airport['lon']],
        popup=popup_text,
        icon=folium.Icon(color=color),
    ).add_to(m)

# Display map
folium_static(m, width=1280, height=800)
