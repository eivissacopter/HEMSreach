import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from datetime import datetime, timedelta
from database import helicopter_bases, airports

def fetch_directory_listing(base_url):
    try:
        response = requests.get(base_url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        if response.status_code == 200:
            return response.text
        else:
            st.warning(f"Failed to fetch directory listing from URL: {base_url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching directory listing from URL: {base_url} - Error: {e}")
        return None

def fetch_file_content(url):
    try:
        response = requests.get(url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        if response.status_code == 200:
            return response.content
        else:
            st.warning(f"Failed to fetch data from URL: {url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from URL: {url} - Error: {e}")
        return None

def find_latest_file(base_url, icao_code):
    directory_listing = fetch_directory_listing(base_url + f"/{icao_code.lower()}/")
    if directory_listing:
        soup = BeautifulSoup(directory_listing, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if f"airport_forecast_{icao_code.lower()}_" in a['href']]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            url = f"{base_url}/{icao_code.lower()}/{latest_file}"
            file_content = fetch_file_content(url)
            return file_content
        else:
            st.warning(f"No forecast files found for {icao_code}.")
    return None

def decode_forecast(data, icao_code):
    for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
        try:
            content = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("All decoding attempts failed.")
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith("DATE;"):
            header_index = i
            break
    else:
        raise ValueError("Header not found in the file.")
    
    data_lines = lines[header_index:]
    rows = [line.split(';') for line in data_lines if len(line.split(';')) > 1]
    num_columns = len(rows[0])
    column_names = [f"{icao_code.upper()}{i:02d}" for i in range(num_columns)]
    df = pd.DataFrame(rows, columns=column_names)
    return df

def parse_forecast(df):
    return df

def find_closest_airport_with_forecast(base_lat, base_lon, available_icao_codes):
    sorted_airports = sorted(airports, key=lambda airport: geodesic((base_lat, base_lon), (airport['lat'], airport['lon'])).kilometers)
    for airport in sorted_airports:
        if airport['icao'].lower() in available_icao_codes:
            return airport
    return None

def extract_icao_codes(directory_listing):
    soup = BeautifulSoup(directory_listing, 'html.parser')
    icao_codes = [a['href'].strip('/').lower() for a in soup.find_all('a', href=True) if len(a['href'].strip('/')) == 4]
    return icao_codes

def get_wind_at_altitude(location):
    base_url = "https://data.dwd.de/aviation/ATM/AirportWxForecast"
    directory_listing = fetch_directory_listing(base_url)
    
    if directory_listing:
        available_icao_codes = set(extract_icao
