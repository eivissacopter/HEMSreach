import streamlit as st
import folium
from streamlit_folium import st_folium
from owslib.wms import WebMapService
import requests

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Initialize Folium map
m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

# Define a function to add WMS layers
def add_wms_layer(m, layer_name):
    wms = WebMapService(server_url, version='1.3.0', username=username, password=password)
    folium.raster_layers.WmsTileLayer(
        url=server_url + '/wms',
        layers=layer_name,
        name=layer_name,
        fmt='image/png',
        transparent=True,
        version='1.3.0',
        attribution="Weather data © 2024 Deutscher Wetterdienst",
        control=True
    ).add_to(m)

# Buttons to add weather overlays
if st.sidebar.button('Show Temperature'):
    add_wms_layer(m, 'dwd:temperature')
if st.sidebar.button('Show Precipitation'):
    add_wms_layer(m, 'dwd:precipitation')
if st.sidebar.button('Show Wind Speed'):
    add_wms_layer(m, 'dwd:wind_speed')

# Display the map
st_folium(m, width=700, height=500)
