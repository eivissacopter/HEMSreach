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

# Sidebar for selecting weather overlays
st.sidebar.title("Select Weather Overlay")
if layers:
    selected_layer_title = st.sidebar.selectbox("Layer", [title for title, name in layers])
    selected_layer_name = next(name for title, name in layers if title == selected_layer_title)

    # Initialize Folium map
    m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

    # Add selected layer to map using WMS
    def add_wms_layer(m, layer_name, layer_title):
        try:
            wms_url = f"{server_url}/geoserver/dwd/ows"
            folium.raster_layers.WmsTileLayer(
                url=wms_url,
                name=layer_title,
                layers=layer_name,
                format='image/png',
                transparent=True,
                version='1.3.0',
                attribution="Weather data © 2024 Deutscher Wetterdienst",
                control=True
            ).add_to(m)
            st.success(f"Layer {layer_title} added successfully")
        except Exception as e:
            st.error(f"Failed to add layer {layer_title}: {e}")

    # Add the selected layer to the map
    add_wms_layer(m, selected_layer_name, selected_layer_title)

    # Display the map
    st_folium(m, width=700, height=500)
else:
    st.sidebar.write("No layers available")
