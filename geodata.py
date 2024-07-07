import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import xmltodict
import requests
from requests.auth import HTTPBasicAuth

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Upload XML file
uploaded_file = st.file_uploader("Choose a GetCapabilities XML file", type="xml")
if uploaded_file:
    xml_content = uploaded_file.read().decode("utf-8")
    data_dict = xmltodict.parse(xml_content)
    layers = data_dict['WMS_Capabilities']['Capability']['Layer']['Layer']
    layer_info = [(layer['Title'], layer['Name']) for layer in layers]

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

    # Sidebar to select layers
    st.sidebar.title("Select Weather Overlays")
    selected_layer = st.sidebar.selectbox("Choose a layer to display", [title for title, name in layer_info])

    # Add the selected layer to the map
    for title, name in layer_info:
        if title == selected_layer:
            add_wms_layer(m, name, title)

    # Load GeoJSON file from URL
    def add_geojson_layer(m, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            geojson_data = response.json()
            folium.GeoJson(
                geojson_data,
                name="MRVA Overlay"
            ).add_to(m)
            st.success("MRVA Overlay added successfully")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch GeoJSON: {e}")
        except json.JSONDecodeError as e:
            st.error(f"Failed to load MRVA Overlay: {e}")
        except Exception as e:
            st.error(f"Failed to add MRVA Overlay: {e}")

    # Sidebar switch to enable/disable GeoJSON overlay
    enable_geojson = st.sidebar.checkbox("Enable MRVA Overlay")

    if enable_geojson:
        geojson_url = 'https://filebin.net/opbm1223wsobw8uf/MRVA.geojson'
        add_geojson_layer(m, geojson_url)

    # Display the map
    st_folium(m, width=700, height=500)
else:
    st.warning("Please upload a GetCapabilities XML file.")
