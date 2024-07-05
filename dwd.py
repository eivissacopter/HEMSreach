import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import folium
from streamlit_folium import st_folium
import io

# Load secrets
data_server = st.secrets["data_server"]
geo_server = st.secrets["geo_server"]

# Single airport for demonstration
airport = "EDDF"

# Function to fetch data via HTTPS
def fetch_data_https(directory_path, file_name):
    try:
        base_url = f"https://{data_server['server']}{directory_path}/{file_name}"
        response = requests.get(base_url, auth=(data_server["user"], data_server["password"]))
        
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Failed to fetch data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Function to get the latest file name via HTTPS
def get_latest_file_name(directory_path):
    try:
        base_url = f"https://{data_server['server']}{directory_path}"
        response = requests.get(base_url, auth=(data_server["user"], data_server["password"]))
        
        if response.status_code == 200:
            file_list = response.text.split('\n')
            if file_list:
                latest_file = sorted(file_list)[-1]
                return latest_file
        else:
            st.error(f"Failed to list files: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return None

# Function to parse the .dat file content and return a DataFrame
def parse_forecast_data(file_content):
    try:
        # Decode the content and split by lines
        lines = file_content.decode('utf-8').strip().split('\n')
        
        # Extract the header row
        headers = lines[4].split(';')[1:-1]
        
        # Extract the data rows starting from the 6th line
        data_rows = []
        for line in lines[5:]:
            data = line.split(';')[1:-1]
            if data:
                data_rows.append(data)
        
        # Create a DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        return df
    except Exception as e:
        st.error(f"Error parsing data: {e}")
        return None

# Function to create and display a folium map centered on EDDF
def create_map():
    # Coordinates for EDDF
    eddf_coords = [50.0379, 8.5622]

    # Create a folium map centered on EDDF
    m = folium.Map(location=eddf_coords, zoom_start=10)

    # Add GeoServer WMS layer
    wms_url = f"https://{geo_server['user']}:{geo_server['password']}@maps.dwd.de/geoserver/dwd/ICON_ADWICE_POLYGONE/ows?"

    folium.raster_layers.WmsTileLayer(
        url=wms_url,
        name='DWD WMS',
        layers='dwd:ICON_ADWICE_POLYGONE',
        attr='DWD',
        fmt='image/png',
        transparent=True,
        version='1.3.0'
    ).add_to(m)

    return m

# Streamlit setup
st.title("Weather Forecast and Map for EDDF")

# Fetch and display the weather forecast data for the airport EDDF
directory_path = f'/aviation/ATM/AirportWxForecast/{airport}'
latest_file = get_latest_file_name(directory_path)

if latest_file:
    file_content = fetch_data_https(directory_path, latest_file)
    if file_content:
        forecast_df = parse_forecast_data(file_content)
        if forecast_df is not None:
            # Display the collected data
            st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.dataframe(forecast_df)
else:
    st.write("No data available")

# Create and display the map
st.write("**Map centered on EDDF**")
map_ = create_map()
st_folium(map_, width=700, height=500)
