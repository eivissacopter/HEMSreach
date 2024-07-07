import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Initialize Folium map
m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

# Define a function to add WMS layers
def add_wms_layer(m, layer_name, layer_title):
    try:
        wms_url = f"{server_url}/geoserver/ows"
        folium.raster_layers.WmsTileLayer(
            url=wms_url,
            name=layer_title,
            layers=layer_name,
            format='image/png',
            transparent=True,
            version='1.3.0',
            attribution="Weather data © 2024 Deutscher Wetterdienst",
            control=True,
            styles='',
            crs='EPSG:4326'
        ).add_to(m)
        st.success(f"Layer {layer_title} added successfully")
    except Exception as e:
        st.error(f"Failed to add layer {layer_title}: {e}")

# Sidebar for selecting weather overlays
st.sidebar.title("Select Weather Overlays")
if st.sidebar.button('Show Temperature'):
    add_wms_layer(m, 'dwd:FX-TT', 'Temperature')
if st.sidebar.button('Show Precipitation'):
    add_wms_layer(m, 'dwd:RRR', 'Precipitation')
if st.sidebar.button('Show Wind Speed'):
    add_wms_layer(m, 'dwd:FX-FX10', 'Wind Speed')

# Display the map
st_folium(m, width=700, height=500)
