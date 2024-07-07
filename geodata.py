import streamlit as st
import folium
from streamlit_folium import st_folium

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Specific layer to be displayed
layer_name = 'dwd:ICON_ADWICE_POLYGONE'
layer_title = 'ICON ADWICE Polygone'

# Initialize Folium map
m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

# Add WMS layer to map
def add_wms_layer(m, layer_name, layer_title):
    try:
        wms_url = f"{server_url}/geoserver/dwd/ows"
        tile_layer = folium.raster_layers.WmsTileLayer(
            url=wms_url,
            layers=layer_name,
            fmt='image/png',
            transparent=True,
            version='1.3.0',
            name=layer_title,
            control=True,
            attribution="Weather data © 2024 Deutscher Wetterdienst"
        )
        tile_layer.add_to(m)
        st.success(f"Layer {layer_title} added successfully")
    except Exception as e:
        st.error(f"Failed to add layer {layer_title}: {e}")

# Add the specified layer to the map
add_wms_layer(m, layer_name, layer_title)

# Display the map
st_folium(m, width=700, height=500)
