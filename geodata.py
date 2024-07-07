import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
import requests
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Fetch layers from GeoServer WMS
def fetch_layers():
    wms_url = f"{server_url}/geoserver/dwd/ows?service=WMS&version=1.3.0&request=GetCapabilities"
    st.write(f"Requesting URL: {wms_url}")  # Debugging output to verify the URL
    try:
        response = requests.get(wms_url, auth=HTTPBasicAuth(username, password))
        response.raise_for_status()  # Raise an error for bad status codes
        tree = ElementTree.fromstring(response.content)
        layers = []
        for layer in tree.findall('.//{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer'):
            title = layer.find('{http://www.opengis.net/wms}Title').text
            name = layer.find('{http://www.opengis.net/wms}Name').text
            layers.append((title, name))
        return layers
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch layers from GeoServer: {e}")
        return []
    except ElementTree.ParseError as e:
        st.error(f"Failed to parse XML response: {e}")
        return []

layers = fetch_layers()

# Initialize Folium map
m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

# Function to add WMS layer to map
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

# Sidebar switches for WMS layers
st.sidebar.title("Select Weather Overlays")
selected_layers = []
for title, name in layers:
    if st.sidebar.checkbox(f"Enable {title}"):
        add_wms_layer(m, name, title)
        selected_layers.append(title)

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
