import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import folium
import geojson
import streamlit as st

def get_latest_xml_url(base_url, auth):
    try:
        response = requests.get(base_url, auth=auth)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        st.error(f"An error occurred: {err}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    xml_files = [a['href'] for a in soup.find_all('a') if a['href'].endswith('.xml')]
    if not xml_files:
        st.error("No XML files found in the directory.")
        return None
    
    latest_file = max(xml_files, key=lambda x: x.split('/')[-1])
    return base_url + latest_file

def fetch_latest_xml(xml_url, auth):
    try:
        response = requests.get(xml_url, auth=auth)
        response.raise_for_status()
        return response.content
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        st.error(f"An error occurred: {err}")
    return None

def xml_to_geojson(xml_data, layer_type):
    ns = {
        'dwd': 'http://www.dwd.de/wv2/exchange-message/1.0',
        'gml': 'http://www.opengis.net/gml/3.2'
    }
    
    root = ET.fromstring(xml_data)
    features = []

    if layer_type == 'NowCastMix':
        for polygon in root.findall('.//gml:Polygon', ns):
            pos_list = polygon.find('.//gml:posList', ns).text.strip().split()
            coords = [(float(pos_list[i+1]), float(pos_list[i])) for i in range(0, len(pos_list), 2)]
            
            status_element = polygon.find('.//gml:description', ns)
            status = status_element.text if status_element is not None else "default"

            feature = geojson.Feature(
                geometry=geojson.Polygon([coords]),
                properties={"status": status}
            )
            features.append(feature)
    elif layer_type == 'Lightning':
        for lightning in root.findall('.//dwd:lightning', ns):
            lat = float(lightning.find('.//dwd:lat', ns).text)
            lon = float(lightning.find('.//dwd:lon', ns).text)
            feature = geojson.Feature(
                geometry=geojson.Point((lon, lat)),
                properties={"status": "lightning"}
            )
            features.append(feature)

    feature_collection = geojson.FeatureCollection(features)
    
    return feature_collection

def style_function(feature):
    status = feature['properties']['status']
    color = {
        "default": "#00000000",  # Transparent for default
        "1": "#FFFF00",        # Yellow for status 1
        "2": "#FFA500",        # Orange for status 2
        "3": "#FF0000",        # Red for status 3
        "4": "#800080",        # Purple for status 4
        "reflectivity": "#0000FF",  # Blue for reflectivity
        "lightning": "#FFA500"  # Orange for lightning
    }.get(status, "#00000000")  # Default to transparent if not specified
    
    return {
        "fillColor": color,
        "color": color,
        "weight": 1,
        "fillOpacity": 0.5 if color != "#00000000" else 0
    }

def add_geojson_to_map(m, geojson_data):
    if geojson_data and geojson_data['features']:
        for feature in geojson_data['features']:
            geom = feature['geometry']
            props = feature['properties']
            
            if geom['type'] == 'Point' and props.get('status') == 'lightning':
                lat, lon = geom['coordinates'][1], geom['coordinates'][0]
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    color='orange',
                    fill=True,
                    fill_color='orange'
                ).add_to(m)
            else:
                folium.GeoJson(
                    feature,
                    style_function=style_function
                ).add_to(m)
    else:
        st.warning("No valid GeoJSON data to add to the map.")
    return m

def add_layers_to_map(m, show_nowcastmix_layer, show_lightning_layer, show_terrain_layer, auth):
    if show_terrain_layer:
        tile_url = "https://nginx.eivissacopter.com/ofma/original/merged/512/latest/{z}/{x}/{y}.png"
        folium.TileLayer(
            tiles=tile_url,
            attr="Custom Tiles",
            name="Openflightmaps Terrain",
            overlay=False,
            control=True
        ).add_to(m)
    
    if show_nowcastmix_layer:
        base_url = "https://data.dwd.de/aviation/Special_application/NCM-A/"
        xml_url = get_latest_xml_url(base_url, auth)
        if xml_url:
            xml_data = fetch_latest_xml(xml_url, auth)
            if xml_data:
                geojson_data = xml_to_geojson(xml_data, 'NowCastMix')
                add_geojson_to_map(m, geojson_data)

    if show_lightning_layer:
        base_url = "https://data.dwd.de/aviation/Lightning_data/"
        xml_url = get_latest_xml_url(base_url, auth)
        if xml_url:
            xml_data = fetch_latest_xml(xml_url, auth)
            if xml_data:
                geojson_data = xml_to_geojson(xml_data, 'Lightning')
                add_geojson_to_map(m, geojson_data)

    return m

# Sample usage in Streamlit
if __name__ == "__main__":
    st.set_page_config(page_title="HEMSreach", page_icon="🚁", layout="wide")
    
    def apply_custom_css():
        st.markdown(
            """
            <style>
            body {
                background-color: #2e2e2e;
                color: white;
            }
            .reportview-container .main .block-container {
                padding: 0;
            }
            .reportview-container .main {
                background: none;
                padding: 0;
            }
            .sidebar .sidebar-content {
                background-color: #3e3e3e;
            }
            .fullScreenMap {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
            }
            .stSlider, .stNumberInput, .stTextInput {
                color: black;
            }
            .stNumberInput, .stTextInput {
                display: inline-block;
                margin-right: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def set_header():
        st.markdown(
            """
            <h1 style='text-align: center;'>
                🚁 HEMSreach 🚁
            </h1>
            """,
            unsafe_allow_html=True
        )

    def create_sidebar(helicopter_bases, airports):
        with st.sidebar:
            base_names = [base['name'] for base in helicopter_bases]
            airport_names = [airport['name'] for airport in airports]

            base_or_airport = st.radio('Select Departure', ['Base', 'Airport'], horizontal=True)

            if base_or_airport == 'Base':
                selected_base_name = st.selectbox('Select Home Base', base_names)
                selected_location = next(base for base in helicopter_bases if base['name'] == selected_base_name)
            else:
                selected_airport_name = st.selectbox('Select Airport', airport_names)
                selected_location = next(airport for airport in airports if airport['name'] == selected_airport_name)

            selected_base_elevation = selected_location['elevation_ft']

            st.markdown("")
            cruise_altitude_ft = st.slider(
                'Cruise Altitude',
                min_value=3000, max_value=10000, value=5000, step=1000,
                format="%d ft"
            )
            total_fuel_kg = st.slider(
                'Total Fuel Upload',
                min_value=400, max_value=723, value=500, step=50,
                format="%d kg"
            )

            selected_time = st.slider("Select time window (hours)", min_value=0, max_value=6, value=1)

            show_terrain_layer = st.checkbox("Terrain")
            show_nowcastmix_layer = st.checkbox("NowCastMix")
            show_lightning_layer = st.checkbox("Lightning")

        return selected_location, total_fuel_kg, cruise_altitude_ft, selected_time, show_nowcastmix_layer, show_lightning_layer, show_terrain_layer

    from streamlit_autorefresh import st_autorefresh
    from wtaloft import get_wind_at_altitude
    from e6b import get_reachable_airports
    from performance import H145D2_PERFORMANCE
    from database import helicopter_bases, airports
    from streamlit_folium import folium_static
    import pandas as pd

    # Fetch authentication credentials from secrets
    data_server = st.secrets["data_server"]
    auth = (data_server["user"], data_server["password"])

    # Set page configuration and custom CSS
    apply_custom_css()

    # Add header
    set_header()

    # Auto-refresh every 30 minutes (1800 seconds)
    st_autorefresh(interval=1800 * 1000, key="data_refresh")

    # Create sidebar and
