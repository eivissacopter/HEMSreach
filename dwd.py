import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# Load secrets from Streamlit configuration
data_server = st.secrets["data_server"]

# List of airports
airports = ["EDDF", "EDFM", "EDFH"]

# Function to fetch directory listing
def fetch_directory_listing(base_url):
    try:
        response = requests.get(base_url, auth=(data_server["user"], data_server["password"]))
        if response.status_code == 200:
            return response.text
        else:
            st.warning(f"Failed to fetch directory listing from URL: {base_url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching directory listing from URL: {base_url} - Error: {e}")
        return None

# Function to fetch file content via HTTPS
def fetch_file_content(url):
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

# Function to find the latest available file by scanning the directory
def find_latest_file(base_url, airport_code):
    directory_listing = fetch_directory_listing(base_url)
    if directory_listing:
        lines = directory_listing.splitlines()
        relevant_files = [line.split()[0] for line in lines if f"_{airport_code}_" in line]
        if relevant_files:
            latest_file = sorted(relevant_files, reverse=True)[0]  # Assuming the first element is the filename
            url = f"{base_url}/{latest_file}"
            file_content = fetch_file_content(url)
            return file_content
    return None

# Streamlit setup
st.title("Latest METAR and TAF for Airports")

# Dictionary to store METAR and TAF data
airport_data = {}

# Base URLs for METAR and TAF directories
metar_base_url = f"https://{data_server['server']}/aviation/OPMET/METAR/DE"
taf_base_url = f"https://{data_server['server']}/aviation/OPMET/TAF/DE"

# Fetch the latest METAR and TAF data for each airport
for airport in airports:
    file_content_metar = find_latest_file(metar_base_url, airport)
    metar_message = parse_metar_data(file_content_metar) if file_content_metar else None

    file_content_taf = find_latest_file(taf_base_url, airport)
    taf_message = parse_taf_data(file_content_taf) if file_content_taf else None

    if metar_message or taf_message:
        airport_data[airport] = {"METAR": metar_message, "TAF": taf_message}

# Display data in a table
if airport_data:
    df = pd.DataFrame.from_dict(airport_data, orient='index')
    st.write(f"Data last updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    st.dataframe(df)
else:
    st.write("No data available for airports with both METAR and TAF")
