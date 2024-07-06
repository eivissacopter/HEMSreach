import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

# Load secrets
data_server = st.secrets["data_server"]

# List of airports
airports = ["EDAC", "EDDR"]

# Function to construct the expected file name based on a given datetime
def construct_file_name_metar(dt, airport_code):
    file_name = f"SADL31_{airport_code}_{dt.strftime('%d%H%M')}"
    return file_name

def construct_file_name_taf(dt, airport_code):
    file_name = f"FTDL31_{airport_code}_{dt.strftime('%d%H%M')}"
    return file_name

# Function to fetch data via HTTPS
def fetch_data_https(directory_path, file_name):
    try:
        base_url = f"https://{data_server['server']}{directory_path}/{file_name}"
        response = requests.get(base_url, auth=(data_server["user"], data_server["password"]))
        
        if response.status_code == 200:
            return response.content
        else:
            st.warning(f"Failed to fetch data from URL: {base_url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from URL: {base_url} - Error: {e}")
        return None

# Function to find the latest available file by iterating over the past few hours
def find_latest_file(directory_path, construct_file_name, airport_code, hours_back=24):
    now = datetime.utcnow()
    for i in range(hours_back):
        dt = now - timedelta(hours=i)
        file_name = construct_file_name(dt, airport_code)
        file_content = fetch_data_https(directory_path, file_name)
        if file_content:
            return file_content
        else:
            # Try variations with additional letters (e.g., SADL31_EDZO_050320_CCA)
            variations = ['CCA', 'CCB', 'CCC', 'CCD', 'CCE']
            for var in variations:
                file_name_variation = f"{file_name}_{var}"
                file_content = fetch_data_https(directory_path, file_name_variation)
                if file_content:
                    return file_content
    return None

# Function to parse the METAR data content
def parse_metar_data(file_content):
    try:
        content = file_content.decode('utf-8').strip()
        metar_message = content.split('METAR')[1].split('=')[0].strip()
        return metar_message
    except Exception as e:
        st.error(f"Error parsing METAR data: {e}")
        return None

# Function to parse the TAF data content
def parse_taf_data(file_content):
    try:
        content = file_content.decode('utf-8').strip()
        taf_message = content.split('TAF')[1].split('=')[0].strip()
        return taf_message
    except Exception as e:
        st.error(f"Error parsing TAF data: {e}")
        return None

# Streamlit setup
st.title("Latest METAR and TAF for Airports")

# Dictionary to store METAR and TAF data
airport_data = {}

# Fetch the latest METAR and TAF data for each airport
for airport in airports:
    directory_path_metar = '/aviation/OPMET/METAR/DE'
    file_content_metar = find_latest_file(directory_path_metar, construct_file_name_metar, airport)
    metar_message = parse_metar_data(file_content_metar) if file_content_metar else None

    directory_path_taf = '/aviation/OPMET/TAF/DE'
    file_content_taf = find_latest_file(directory_path_taf, construct_file_name_taf, airport)
    taf_message = parse_taf_data(file_content_taf) if file_content_taf else None

    if metar_message and taf_message:
        airport_data[airport] = {"METAR": metar_message, "TAF": taf_message}

# Display data in a table
if airport_data:
    df = pd.DataFrame.from_dict(airport_data, orient='index')
    st.write(f"Data last updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    st.dataframe(df)
else:
    st.write("No data available for airports with both METAR and TAF")

# Function to create and display a folium map centered on EDDF
def create_map():
    # Coordinates for EDDF
    eddf_coords = [50.0379, 8.5622]

    # Create a folium map centered on EDDF
    m = folium.Map(location=eddf_coords, zoom_start=10)
    return m

# Create and display the map
st.write("**Map centered on EDDF**")
map_ = create_map()
st_folium(map_, width=700, height=500)
