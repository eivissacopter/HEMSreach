import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import requests
import math
from datetime import datetime, timedelta
from database import helicopter_bases, airports
import folium
from streamlit_folium import folium_static
import pytz
import pytaf
import os
import json
from bs4 import BeautifulSoup

###########################################################################################

# Set the page configuration for wide mode and dark theme
st.set_page_config(page_title="IFR Rescue Radius", page_icon=":helicopter:", layout="wide")

# Custom CSS to make the map full-screen and as the background, and to engage dark mode
st.markdown(
    """
    <style>
    body {
        background-color: #2e2e2e;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar for inputs
st.sidebar.header("Flight Parameters")

# Selection of helicopter base
base_selection = st.sidebar.selectbox("Select Helicopter Base", list(helicopter_bases.keys()))
selected_base = helicopter_bases[base_selection]

# Time slider
current_time = datetime.utcnow()
start_time = current_time - timedelta(hours=12)
end_time = current_time + timedelta(hours=12)
selected_time = st.sidebar.slider("Select Time", min_value=start_time, max_value=end_time, value=current_time, format="YYYY-MM-DD HH:mm")

# Altitude selection
cruise_altitude = st.sidebar.slider("Cruise Altitude (ft)", min_value=3000, max_value=10000, step=1000)

# Function to fetch weather data
def fetch_weather_data(icao_code):
    url = f"https://aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&stationString={icao_code}&hoursBeforeNow=2"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        metar = soup.find_all('METAR')[0]
        wind_dir = int(metar.wind_dir_degrees.string)
        wind_speed = int(metar.wind_speed_kt.string)
        fz_lvl = 10000  # Assuming a default freezing level for the example
        return wind_dir, wind_speed, fz_lvl
    return None, None, None

# Calculate closest airport
def get_closest_airport(base_lat, base_lon):
    min_distance = float('inf')
    closest_airport = None
    for airport in airports:
        distance = math.sqrt((base_lat - airport['lat'])**2 + (base_lon - airport['lon'])**2)
        if distance < min_distance:
            min_distance = distance
            closest_airport = airport
    return closest_airport

closest_airport = get_closest_airport(selected_base['lat'], selected_base['lon'])
if closest_airport:
    wind_dir, wind_speed, freezing_level = fetch_weather_data(closest_airport['icao'])

    if wind_dir is not None and wind_speed is not None:
        st.sidebar.write(f"Wind Direction @5000FT: {wind_dir}°")
        st.sidebar.write(f"Wind Speed @5000FT: {wind_speed} kt")
        st.sidebar.write(f"Freezing Level: {freezing_level} ft")

        # Example reachable airports data using the wind data
        reachable_airports = [
            {"Airport": "Example Airport", "Distance (NM)": 50, "Time (hours)": 0.5, "Track (°)": wind_dir, "Ground Speed (kt)": wind_speed, "Fuel Required (kg)": 500, "METAR": "Example METAR", "TAF": "Example TAF"}
        ]

        # Display reachable airports
        st.markdown("### Reachable Airports")
        df_reachable = pd.DataFrame(reachable_airports)
        st.table(df_reachable)
else:
    st.error("No closest airport found with available forecast data.")

###########################################################################################

# Map visualization
m = folium.Map(location=[selected_base['lat'], selected_base['lon']], zoom_start=7)

# Add helicopter base marker
folium.Marker(
    location=[selected_base['lat'], selected_base['lon']],
    popup=f"Helicopter Base: {base_selection}",
    icon=folium.Icon(color="red", icon="helicopter")
).add_to(m)

# Add reachable airports markers
if reachable_airports:
    for airport in reachable_airports:
        folium.Marker(
            location=[airport['lat'], airport['lon']],
            popup=f"Airport: {airport['name']}",
            icon=folium.Icon(color="blue", icon="plane")
        ).add_to(m)

# Display map
folium_static(m, width=1440, height=720)

###########################################################################################

# Ensure the columns exist before trying to highlight
if reachable_airports:
    decoded_airports_data = []

    for airport_data in reachable_airports:
        distance_nm = f"{airport_data['Distance (NM)']:.2f} NM"
        time_hours = int(airport_data["Time (hours)"])
        time_minutes = int((airport_data["Time (hours)"] - time_hours) * 60)
        time_hhmm = f"{time_hours:02d}:{time_minutes:02d}"
        track_deg = f"{int(airport_data['Track (°)']):03d}°"
        ground_speed_kt = f"{int(airport_data['Ground Speed (kt)']):03d} kt"
        fuel_required_kg = f"{int(airport_data['Fuel Required (kg)'])} kg"
        metar_raw = airport_data["METAR"]
        taf_raw = airport_data["TAF"]

        decoded_airports_data.append({
            "Airport": airport_data["Airport"],
            "Distance (NM)": distance_nm,
            "Time (hours)": time_hhmm,
            "Track (°)": track_deg,
            "Ground Speed (kt)": ground_speed_kt,
            "Fuel Required (kg)": fuel_required_kg,
            "METAR": metar_raw,
            "TAF": taf_raw
        })

    df_decoded = pd.DataFrame(decoded_airports_data)
    st.markdown("### METAR/TAF Data")
    st.markdown(df_decoded.to_html(escape=False), unsafe_allow_html=True)
else:
    df_decoded = pd.DataFrame(columns=["Airport", "Distance (NM)", "Time (hours)", "Track (°)", "Ground Speed (kt)", "Fuel Required (kg)", "METAR", "TAF"])
    st.markdown("### METAR/TAF Data")
    st.table(df_decoded)
