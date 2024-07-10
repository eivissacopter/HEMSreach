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
import geopandas as gpd
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

###########################################################################################

with st.sidebar:
    base_names = [base['name'] for base in helicopter_bases]
    airport_names = [airport['name'] for airport in airports]

    # Toggle switch to choose between Bases and Airports
    base_or_airport = st.radio('Select Departure', ['Base', 'Airport'], horizontal=True)

    # Input field for selecting base or airport
    if base_or_airport == 'Base':
        selected_base_name = st.selectbox('Select Home Base', base_names)
        selected_location = next(base for base in helicopter_bases if base['name'] == selected_base_name)
    else:
        selected_airport_name = st.selectbox('Select Airport', airport_names)
        selected_location = next(airport for airport in airports if airport['name'] == selected_airport_name)

    selected_base_elevation = selected_location['elevation_ft']


    st.markdown("")
    total_fuel_kg = st.slider(
        'Total Fuel Upload',
        min_value=400, max_value=723, value=500, step=50,
        format="%d kg"
    )
    cruise_altitude_ft = st.slider(
        'Cruise Altitude',
        min_value=3000, max_value=10000, value=5000, step=1000,
        format="%d ft"
    )

###########################################################################################

# BASE / AIRPORT EXPORT to WINDALOFT

# WINDALOFT to E6B Calculate reachable

# E6B EXPORT Reachable to 



###########################################################################################

# Sidebar for layer toggles
with st.sidebar:
    st.markdown("### Select Layers")
    geojson_selected = st.checkbox('MRVA Layer')

###########################################################################################

# Correct URL for the GeoJSON layer
geojson_layer_url = "https://nginx.eivissacopter.com/mrva/mvra.geojson"

# Function to fetch GeoJSON file from the specific URL
def fetch_geojson_layer(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning(f"GeoJSON layer not found at URL: {url}")
            return None
        else:
            st.warning(f"Failed to fetch GeoJSON layer from URL: {url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching GeoJSON layer from URL: {url} - Error: {e}")
        return None

###########################################################################################

# Create map centered on selected location using custom EPSG3857 tiles
m = folium.Map(
    location=[selected_location['lat'], selected_location['lon']],
    zoom_start=7,
    tiles=None,  # Disable default tiles
    crs='EPSG3857'  # Use EPSG3857 projection
)

# Add custom tile layer
tile_url = "https://nginx.eivissacopter.com/ofma/clip/merged/512/latest/{z}/{x}/{y}.png"
folium.TileLayer(
    tiles=tile_url,
    attr="Custom Tiles",
    name="Custom EPSG3857 Tiles",
    overlay=False,
    control=True
).add_to(m)

# Add GeoJSON layer if selected
if geojson_selected:
    geojson_layer = fetch_geojson_layer(geojson_layer_url)
    if geojson_layer:
        folium.GeoJson(
            geojson_layer,
            name="MRVA Layer",
            control=True
        ).add_to(m)

# Add reachable airports to the map
reachable_airports_data = []
for airport, distance, bearing, ground_speed_kt, time_to_airport_hours in reachable_airports:
    metar_data, taf_data = fetch_metar_taf_data(airport['icao'], AVWX_API_KEY)

    if metar_data and taf_data:
        metar_raw = metar_data if isinstance(metar_data, str) else metar_data.get('raw', '')
        taf_raw = taf_data if isinstance(taf_data, str) else taf_data.get('raw', '')

        # Calculate descent time using destination airport elevation
        airport_elevation_ft = airport.get('elevation', 500)  # Default to 500ft if not available
        descent_time_hours = (cruise_altitude_ft - airport_elevation_ft) / descent_rate_fpm / 60

        # Calculate fuel burn for descent
        descent_fuel_burn = descent_time_hours * descend_performance['fuel_burn_kgph']

        # Recalculate remaining trip fuel after descent
        remaining_trip_fuel_kg = trip_fuel_kg - (climb_fuel_burn + descent_fuel_burn)

        # Calculate cruise time based on remaining fuel
        cruise_time_hours = remaining_trip_fuel_kg / cruise_fuel_burn_rate

        fuel_required = time_to_airport_hours * cruise_fuel_burn_rate

        reachable_airports_data.append({
            "Airport": f"{airport['name']} ({airport['icao']})",
            "METAR": metar_raw,
            "TAF": taf_raw,
            "Distance (NM)": round(distance, 2),
            "Time (hours)": round(time_to_airport_hours, 2),
            "Track (°)": round(bearing, 2),
            "Ground Speed (kt)": round(ground_speed_kt, 2),
            "Fuel Required (kg)": round(fuel_required, 2),
            "lat": airport['lat'],
            "lon": airport['lon']
        })
        
        popup_text = f"{airport['name']} ({airport['icao']})"
        folium.Marker(
            location=[airport['lat'], airport['lon']],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="plane"),
        ).add_to(m)

# Add LayerControl to map
folium.LayerControl().add_to(m)

# Display map
folium_static(m, width=1440, height=720)

###########################################################################################

# Ensure the columns exist before trying to highlight
if reachable_airports_data:
    # Format the data with units and appropriate rounding
    decoded_airports_data = []

    for airport_data in reachable_airports_data:
        distance_nm = f"{airport_data['Distance (NM)']:.2f} NM"
        time_hours = int(airport_data["Time (hours)"])
        time_minutes = int((airport_data["Time (hours)"] - time_hours) * 60)
        time_hhmm = f"{time_hours:02d}:{time_minutes:02d}"
        track_deg = f"{int(airport_data['Track (°)']):03d}°"
        ground_speed_kt = f"{int(airport_data['Ground Speed (kt)']):03d} kt"
        fuel_required_kg = f"{int(airport_data['Fuel Required (kg)'])} kg"

        metar_raw = airport_data["METAR"]
        taf_raw = airport_data["TAF"]
        
        # Add the raw METAR and TAF data directly
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

    # Display the table with the raw METAR and TAF data
    st.markdown("### METAR/TAF Data")
    st.markdown(df_decoded.to_html(escape=False), unsafe_allow_html=True)
else:
    df_decoded = pd.DataFrame(columns=["Airport", "Distance (NM)", "Time (hours)", "Track (°)", "Ground Speed (kt)", "Fuel Required (kg)", "METAR", "TAF"])

    # Display the table
    st.markdown("### METAR/TAF Data")
    st.table(df_decoded)
