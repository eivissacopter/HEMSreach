import streamlit as st
import folium
from streamlit_folium import st_folium
import xmltodict
import requests
from requests.auth import HTTPBasicAuth

# Load secrets from secrets.toml
server_url = st.secrets["geoserver"]["server"]
username = st.secrets["geoserver"]["username"]
password = st.secrets["geoserver"]["password"]

st.title("Weather Overlay Map")

# Recursive function to extract layers and bounding boxes
def extract_wmts_layers(contents):
    extracted_layers = []
    for layer in contents.get('Layer', []):
        title = layer.get('ows:Title')
        name = layer.get('ows:Identifier')
        if title and name:
            extracted_layers.append((title, name))
    return extracted_layers

# Upload WMTS GetCapabilities XML file
uploaded_file_wmts = st.file_uploader("Choose a WMTS GetCapabilities XML file", type="xml")
if uploaded_file_wmts:
    xml_content_wmts = uploaded_file_wmts.read().decode("utf-8")
    
    try:
        data_dict_wmts = xmltodict.parse(xml_content_wmts)
        contents = data_dict_wmts['Capabilities']['Contents']
        wmts_layer_info = extract_wmts_layers(contents)

        if not wmts_layer_info:
            st.error("No WMTS layers found in the GetCapabilities XML.")

        # Sidebar to select WMTS layers
        st.sidebar.title("Select Weather Overlays (WMTS)")
        selected_wmts_layer_title = st.sidebar.selectbox("Choose a WMTS layer to display", [title for title, name in wmts_layer_info])

        # Initialize Folium map with a default location and zoom level
        default_location = [50, 10]
        default_zoom_start = 3
        m = folium.Map(location=default_location, zoom_start=default_zoom_start, control_scale=True)

        # Function to add WMTS layer to map
        def add_wmts_layer(m, layer_name, layer_title):
            try:
                wmts_url = f"{server_url}/geoserver/gwc/service/wmts"
                wmts_layer = folium.raster_layers.WmtsTileLayer(
                    url=wmts_url,
                    layer=layer_name,
                    name=layer_title,
                    fmt='image/png',
                    transparent=True,
                    version='1.0.0',
                    tilematrixset='EPSG:3857',  # Adjust the tile matrix set according to the layer's configuration
                    control=True,
                    opacity=0.6  # Adjust opacity for better visibility
                )
                wmts_layer.add_to(m)
                st.success(f"WMTS layer {layer_title} added successfully")
                st.write(f"Added WMTS layer: {layer_name} ({layer_title})")
            except Exception as e:
                st.error(f"Failed to add WMTS layer {layer_title}: {e}")
                st.write(e)

        # Add the selected WMTS layer to the map
        for title, name in wmts_layer_info:
            if title == selected_wmts_layer_title:
                add_wmts_layer(m, name, title)

        # Display the map with layer control
        folium.LayerControl().add_to(m)
        st_folium(m, width=700, height=500)

    except Exception as e:
        st.error(f"Failed to parse the WMTS GetCapabilities XML: {e}")
        st.write(e)
else:
    st.warning("Please upload a WMTS GetCapabilities XML file.")
