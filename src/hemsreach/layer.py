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
    
    # Find all links and identify the latest XML file
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
        'gml': 'http://www.opengis.net/gml/3.2',
        'konrad3d': 'http://www.dwd.de/radar/konrad3d'
    }
    
    root = ET.fromstring(xml_data)
    features = []

    if layer_type == 'NowCastMix':
        for polygon in root.findall('.//gml:Polygon', ns):
            pos_list = polygon.find('.//gml:posList', ns).text.strip().split()
            coords = [(float(pos_list[i]), float(pos_list[i+1])) for i in range(0, len(pos_list), 2)]
            
            status_element = polygon.find('.//dwd:status', ns)
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
    elif layer_type == 'Konrad3D':
        for cell in root.findall('.//cells/feature', ns):
            lat = float(cell.find('.//latitude', ns).text)
            lon = float(cell.find('.//longitude', ns).text)
            feature = geojson.Feature(
                geometry=geojson.Point((lon, lat)),
                properties={"status": "konrad3d"}
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
        "lightning": "#FFFFFF",  # White for lightning
        "konrad3d": "#00FF00"  # Green for Konrad3D
    }.get(status, "#00000000")  # Default to transparent if not specified
    
    return {
        "fillColor": color,
        "color": color,
        "weight": 1,
        "fillOpacity": 0.5 if color != "#00000000" else 0
    }

def add_geojson_to_map(m, geojson_data):
    if geojson_data and geojson_data['features']:
        folium.GeoJson(
            geojson_data,
            name="XML Layer",
            style_function=style_function
        ).add_to(m)
    else:
        st.warning("No valid GeoJSON data to add to the map.")
    return m

def add_layers_to_map(m, show_nowcastmix_layer, show_lightning_layer, show_konrad3d_layer, show_terrain_layer, auth):
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

    if show_konrad3d_layer:
        base_url = "https://data.dwd.de/radar/konrad3d/"
        xml_url = get_latest_xml_url(base_url, auth)
        if xml_url:
            xml_data = fetch_latest_xml(xml_url, auth)
            if xml_data:
                geojson_data = xml_to_geojson(xml_data, 'Konrad3D')
                add_geojson_to_map(m, geojson_data)

    return m
