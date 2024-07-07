import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Fetch layers from GeoServer WMTS
def fetch_layers():
    wmts_url = f"{server_url}/geoserver/dwd/gwc/service/wmts?REQUEST=GetCapabilities"
    st.write(f"Requesting URL: {wmts_url}")  # Debugging output to verify the URL
    try:
        response = requests.get(wmts_url, auth=HTTPBasicAuth(username, password))
        response.raise_for_status()  # Raise an error for bad status codes
        tree = ElementTree.fromstring(response.content)
        layers = []
        for layer in tree.findall('.//{http://www.opengis.net/wmts/1.0}Layer'):
            title = layer.find('{http://www.opengis.net/ows/1.1}Title').text
            identifier = layer.find('{http://www.opengis.net/ows/1.1}Identifier').text
            layers.append((title, identifier))
        return layers
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch layers from GeoServer: {e}")
        return []
    except ElementTree.ParseError as e:
        st.error(f"Failed to parse XML response: {e}")
        return []

layers = fetch_layers()

# Sidebar for selecting weather overlays
st.sidebar.title("Select Weather Overlay")
if layers:
    selected_layer_title = st.sidebar.selectbox("Layer", [title for title, identifier in layers])
    selected_layer_identifier = next(identifier for title, identifier in layers if title == selected_layer_title)

    # Initialize Folium map
    m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

    # Add selected layer to map using WMTS
    def add_wmts_layer(m, layer_identifier, layer_title):
        try:
            wmts_url = f"{server_url}/geoserver/gwc/service/wmts"
            folium.raster_layers.WmtsTileLayer(
                url=wmts_url,
                layer=layer_identifier,
                name=layer_title,
                tilematrixset='EPSG:4326',  # Adjust the tile matrix set as needed
                format='image/png',
                transparent=True,
                attribution="Weather data © 2024 Deutscher Wetterdienst"
            ).add_to(m)
            st.success(f"Layer {layer_title} added successfully")
        except Exception as e:
            st.error(f"Failed to add layer {layer_title}: {e}")

    # Add the selected layer to the map
    add_wmts_layer(m, selected_layer_identifier, selected_layer_title)

    # Display the map
    st_folium(m, width=700, height=500)
else:
    st.sidebar.write("No layers available")
