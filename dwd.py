import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Load secrets from Streamlit configuration
data_server = st.secrets["data_server"]

# List of airports
airports = ["EDDF", "EDFM", "EDFH"]

# Function to fetch data via HTTPS
def fetch_data_https(url):
    try:
        response = requests.get(url, auth=(data_server["user"], data_server["password"]))
        if response.status_code == 200:
            return response.content
        else:
            st.warning(f"Failed to fetch data from URL: {url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from URL: {url} - Error: {e}")
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

# Function to find the latest available file by iterating over the past few hours
def find_latest_file(base_url, file_prefix, hours_back=24):
    now = datetime.utcnow()
    for i in range(hours_back):
        dt = now - timedelta(hours=i)
        date_time_str = dt.strftime('%d%H%M')
        for suffix in ['', '_CCA', '_CCB', '_CCC', '_CCD', '_CCE']:  # Variations with additional letters
            url = f"{base_url}/{file_prefix}_{date_time_str}{suffix}"
            file_content = fetch_data_https(url)
            if file_content:
                return file_content
    return None

# Streamlit setup
st.title("Latest METAR and TAF for Airports")

# Dictionary to store METAR and TAF data
airport_data = {}

# Fetch the latest METAR and TAF data for each airport
for airport in airports:
    metar_base_url = f"https://{data_server['server']}/aviation/OPMET/METAR/DE"
    file_content_metar = find_latest_file(metar_base_url, f"SADL31_{airport}")
    metar_message = parse_metar_data(file_content_metar) if file_content_metar else None

    taf_base_url = f"https://{data_server['server']}/aviation/OPMET/TAF/DE"
    file_content_taf = find_latest_file(taf_base_url, f"FTDL31_{airport}")
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

