import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os

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
        folium.raster_layers.WmsTileLayer(
            url=wms_url,
            layers=layer_name,
            fmt='image/png',
            transparent=True,
            version='1.3.0',
            name=layer_title
        ).add_to(m)
        st.success(f"Layer {layer_title} added successfully")
    except Exception as e:
        st.error(f"Failed to add layer {layer_title}: {e}")

# Add the specified layer to the map
add_wms_layer(m, layer_name, layer_title)

# Load GeoJSON file
def add_geojson_layer(m, geojson_path):
    try:
        if not os.path.exists(geojson_path):
            st.error(f"GeoJSON file not found: {geojson_path}")
            return
        st.write(f"GeoJSON file found: {geojson_path}")  # Debugging output
        with open(geojson_path) as f:
            geojson_content = f.read()
            st.write(f"GeoJSON content: {geojson_content[:500]}...")  # Display first 500 chars
            geojson_data = json.loads(geojson_content)
        folium.GeoJson(
            geojson_data,
            name="MRVA Overlay"
        ).add_to(m)
        st.success("MRVA Overlay added successfully")
    except json.JSONDecodeError as e:
        st.error(f"Failed to load MRVA Overlay: {e}")
    except Exception as e:
        st.error(f"Failed to add MRVA Overlay: {e}")

# Sidebar switch to enable/disable GeoJSON overlay
enable_geojson = st.sidebar.checkbox("Enable MRVA Overlay")

if enable_geojson:
    geojson_path = os.path.join(os.path.dirname(__file__), 'mrva.geojson')  # Ensure the path is correct
    st.write(f"GeoJSON path: {geojson_path}")  # Debugging output to verify the path
    add_geojson_layer(m, geojson_path)

# Display the map
st_folium(m, width=700, height=500)
