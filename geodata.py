import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from requests.auth import HTTPBasicAuth

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Initialize Folium map
m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

# Define a function to add WMS layers
def add_wms_layer(m, layer_name):
    wms_url = f"{server_url}/wms"
    folium.raster_layers.WmsTileLayer(
        url=wms_url,
        name=layer_name,
        layers=layer_name,
        fmt='image/png',
        transparent=True,
        version='1.3.0',
        attribution="Weather data © 2024 Deutscher Wetterdienst",
        control=True,
        opacity=0.5,
        overlay=True,
        crs='EPSG3857'
    ).add_to(m)

# Sidebar for selecting weather overlays
st.sidebar.title("Select Weather Overlays")
if st.sidebar.button('Show Temperature'):
    add_wms_layer(m, 'dwd:temperature')
if st.sidebar.button('Show Precipitation'):
    add_wms_layer(m, 'dwd:precipitation')
if st.sidebar.button('Show Wind Speed'):
    add_wms_layer(m, 'dwd:wind_speed')

# Display the map
st_data = st_folium(m, width=700, height=500)

# Log the folium map object to help with debugging if needed
st.write(st_data)
