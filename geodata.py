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
def extract_layers(layers):
    extracted_layers = []
    for layer in layers:
        if 'Layer' in layer:
            sublayers = layer['Layer'] if isinstance(layer['Layer'], list) else [layer['Layer']]
            extracted_layers.extend(extract_layers(sublayers))
        else:
            title = layer.get('Title')
            name = layer.get('Name')
            bbox = layer.get('EX_GeographicBoundingBox')
            if title and name:
                extracted_layers.append((title, name, bbox))
    return extracted_layers

# Upload XML file
uploaded_file = st.file_uploader("Choose a GetCapabilities XML file", type="xml")
if uploaded_file:
    xml_content = uploaded_file.read().decode("utf-8")
    
    try:
        data_dict = xmltodict.parse(xml_content)
        layers = data_dict['WMS_Capabilities']['Capability']['Layer']['Layer']
        
        if not isinstance(layers, list):
            layers = [layers]

        layer_info = extract_layers(layers)

        if not layer_info:
            st.error("No layers found in the GetCapabilities XML.")

        # Initialize Folium map
        m = folium.Map(location=[50, 10], zoom_start=6, control_scale=True)

        # Function to add WMS layer to map
        def add_wms_layer(m, layer_name, layer_title, bbox):
            try:
                wms_url = f"{server_url}/geoserver/dwd/ows"
                wms_layer = folium.raster_layers.WmsTileLayer(
                    url=wms_url,
                    layers=layer_name,
                    fmt='image/png',
                    transparent=True,
                    version='1.3.0',
                    name=layer_title,
                    control=True
                )
                wms_layer.add_to(m)
                st.success(f"Layer {layer_title} added successfully")
                st.write(f"Added WMS layer: {layer_name} ({layer_title})")

                # Fit map to layer bounds if bbox is available
                if bbox:
                    bounds = [[float(bbox['southBoundLatitude']), float(bbox['westBoundLongitude'])],
                              [float(bbox['northBoundLatitude']), float(bbox['eastBoundLongitude'])]]
                    m.fit_bounds(bounds)
            except Exception as e:
                st.error(f"Failed to add layer {layer_title}: {e}")

        # Sidebar to select layers
        st.sidebar.title("Select Weather Overlays")
        selected_layer_title = st.sidebar.selectbox("Choose a layer to display", [title for title, name, bbox in layer_info])

        # Add the selected layer to the map
        for title, name, bbox in layer_info:
            if title == selected_layer_title:
                add_wms_layer(m, name, title, bbox)

        # Display the map with layer control
        folium.LayerControl().add_to(m)
        st_folium(m, width=700, height=500)

    except Exception as e:
        st.error(f"Failed to parse the GetCapabilities XML: {e}")
else:
    st.warning("Please upload a GetCapabilities XML file.")
