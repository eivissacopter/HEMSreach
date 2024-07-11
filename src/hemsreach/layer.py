import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import folium
import os
import geojson

def get_latest_xml_url(base_url):
    response = requests.get(base_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links and identify the latest XML file
    xml_files = [a['href'] for a in soup.find_all('a') if a['href'].endswith('.xml')]
    if not xml_files:
        raise ValueError("No XML files found in the directory.")
    
    latest_file = max(xml_files, key=lambda x: x.split('/')[-1])
    return os.path.join(base_url, latest_file)

def fetch_latest_xml(xml_url):
    response = requests.get(xml_url)
    response.raise_for_status()
    return response.content

def xml_to_geojson(xml_data):
    ns = {
        'dwd': 'http://www.dwd.de/wv2/exchange-message/1.0',
        'gml': 'http://www.opengis.net/gml/3.2'
    }
    
    root = ET.fromstring(xml_data)
    features = []

    for polygon in root.findall('.//gml:Polygon', ns):
        pos_list = polygon.find('.//gml:posList', ns).text.strip().split()
        coords = [[(float(pos_list[i+1]), float(pos_list[i])) for i in range(0, len(pos_list), 2)]]
        
        feature = geojson.Feature(
            geometry=geojson.Polygon(coords)
        )
        features.append(feature)

    feature_collection = geojson.FeatureCollection(features)
    return feature_collection

def add_geojson_to_map(m, geojson_data):
    folium.GeoJson(geojson_data, name="XML Layer").add_to(m)
    return m

def add_layers_to_map(m, show_xml_layer, show_terrain_layer):
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
        xml_url = get_latest_xml_url("https://data.dwd.de/aviation/Special_application/NCM-A/")
        xml_data = fetch_latest_xml(xml_url)
        geojson_data = xml_to_geojson(xml_data)
        add_geojson_to_map(m, geojson_data)

    return m
