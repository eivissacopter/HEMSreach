import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import folium
import os

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

def extract_polygons_from_xml(xml_data):
    ns = {
        'dwd': 'http://www.dwd.de/wv2/exchange-message/1.0',
        'gml': 'http://www.opengis.net/gml/3.2'
    }
    
    root = ET.fromstring(xml_data)
    polygons = []

    for polygon in root.findall('.//gml:Polygon', ns):
        pos_list = polygon.find('.//gml:posList', ns).text.strip().split()
        coords = [(float(pos_list[i+1]), float(pos_list[i])) for i in range(0, len(pos_list), 2)]
        polygons.append(coords)

    return polygons

def add_polygons_to_map(m, polygons):
    for coords in polygons:
        folium.Polygon(locations=coords, color='blue', fill=True, fill_opacity=0.4).add_to(m)
    return m
