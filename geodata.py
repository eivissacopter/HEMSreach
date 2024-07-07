import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import xmltodict

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Parse the getcapabilities XML file
def parse_getcapabilities(xml_file):
    with open(xml_file, 'r') as file:
        xml_content = file.read()
    data_dict = xmltodict.parse(xml_content)
    layers = data_dict['WMS_Capabilities']['Capability']['Layer']['Layer']
    layer_info = []
    for layer in layers:
        name = layer['Name']
        title = layer['Title']
        layer_info.append((title, name))
    return layer_info

layers = parse_getcapabilities('getcapabilities_1.3.0.xml')

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

# Load GeoJSON file
def add_geojson_layer(m, geojson_path):
    try:
        with open(geojson_path) as f:
            geojson_data = json.load(f)
        folium.GeoJson(
            geojson_data,
            name="MRVA Overlay"
        ).add_to(m)
        st.success("MRVA Overlay added successfully")
    except json.JSONDecodeError as e:
        st.error(f"Failed to load MRVA Overlay: {e}")
    except Exception as e:
        st.error(f"Failed to add MRVA Overlay: {e}")

# Sidebar to select layers
st.sidebar.title("Select Weather Overlays")
selected_layer = st.sidebar.selectbox("Choose a layer to display", [title for title, name in layers])

# Add the selected layer to the map
for title, name in layers:
    if title == selected_layer:
        add_wms_layer(m, name, title)

# Sidebar switch to enable/disable GeoJSON overlay
enable_geojson = st.sidebar.checkbox("Enable MRVA Overlay")

if enable_geojson:
    geojson_path = 'mrva.geojson'  # Ensure the path is correct
    add_geojson_layer(m, geojson_path)

# Display the map
st_folium(m, width=700, height=500)
