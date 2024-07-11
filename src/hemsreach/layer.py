import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import folium
import geojson
import streamlit as st

def get_latest_xml_urls(base_url, auth, num_files=1):
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
    
    # Find all links and identify the latest XML files
    xml_files = [a['href'] for a in soup.find_all('a') if a['href'].endswith('.xml')]
    if not xml_files:
        st.error("No XML files found in the directory.")
        return None
    
    latest_files = sorted(xml_files, key=lambda x: x.split('/')[-1], reverse=True)[:num_files]
    return [base_url + file for file in latest_files]

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

def xml_to_geojson(xml_data, layer_type, color='orange'):
    ns = {
        'dwd': 'http://www.flugwetter.de/blitzdaten',
        'gml': 'http://www.opengis.net/gml/3.2',
    }
    
    root = ET.fromstring(xml_data)
    features = []

    if layer_type == 'Show XML Layer':
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
                properties={"status": "lightning", "color": color}
            )
            features.append(feature)

    feature_collection = geojson.FeatureCollection(features)
    
    return feature_collection

def add_geojson_to_map(m, geojson_data):
    if geojson_data and geojson_data['features']:
        for feature in geojson_data['features']:
            geom = feature['geometry']
            props = feature['properties']
            
            if geom['type'] == 'Point' and props.get('status') == 'lightning':
                lat, lon = geom['coordinates'][1], geom['coordinates'][0]
                color = props.get('color', 'orange')
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7
                ).add_to(m)
            else:
                folium.GeoJson(
                    feature,
                    style_function=style_function
                ).add_to(m)
    else:
        st.warning("No valid GeoJSON data to add to the map.")
    return m

def add_layers_to_map(m, show_xml_layer, show_lightning_layer, show_terrain_layer, auth):
    if show_terrain_layer:
        tile_url = "https://nginx.eivissacopter.com/ofma/original/merged/512/latest/{z}/{x}/{y}.png"
        folium.TileLayer(
            tiles=tile_url,
            attr="Custom Tiles",
            name="Openflightmaps Terrain",
            overlay=False,
            control=True
        ).add_to(m)
    
    if show_xml_layer:
        base_url = "https://data.dwd.de/aviation/Special_application/NCM-A/"
        xml_url = get_latest_xml_urls(base_url, auth)[0]
        if xml_url:
            xml_data = fetch_latest_xml(xml_url, auth)
            if xml_data:
                geojson_data = xml_to_geojson(xml_data, 'Show XML Layer')
                add_geojson_to_map(m, geojson_data)

    if show_lightning_layer:
        base_url = "https://data.dwd.de/aviation/Lightning_data/"
        xml_urls = get_latest_xml_urls(base_url, auth, num_files=3)
        colors = ['yellow', 'orange', 'red']
        for xml_url, color in zip(xml_urls, colors):
            if xml_url:
                xml_data = fetch_latest_xml(xml_url, auth)
                if xml_data:
                    geojson_data = xml_to_geojson(xml_data, 'Lightning', color)
                    add_geojson_to_map(m, geojson_data)

    return m
