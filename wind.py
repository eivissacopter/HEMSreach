import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from io import StringIO
from bs4 import BeautifulSoup

# Function to fetch directory listing
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

# Function to fetch file content via HTTPS
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

# Function to find the latest available file by scanning the directory
def find_latest_file(base_url, icao_code):
    directory_listing = fetch_directory_listing(base_url + f"/{icao_code}/")
    if directory_listing:
        soup = BeautifulSoup(directory_listing, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if f"airport_forecast_{icao_code}_" in a['href']]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            url = f"{base_url}/{icao_code}/{latest_file}"
            file_content = fetch_file_content(url)
            return file_content
    return None

# Function to decode the forecast data
def decode_forecast(data):
    # Try multiple encodings
    for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
        try:
            content = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("All decoding attempts failed.")
    
    lines = content.split('\n')
    
    # Find the line with the header
    header_index = None
    for i, line in enumerate(lines):
        if line.startswith("DATE;"):
            header_index = i
            break

    if header_index is None:
        raise ValueError("Header not found in the file.")

    header = lines[header_index].split(';')
    
    # Make column names unique
    cols = pd.Series(header)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    header = cols.tolist()
    
    rows = [line.split(';') for line in lines[header_index + 1:] if len(line.split(';')) == len(header)]
    
    df = pd.DataFrame(rows, columns=header)
    return df

# Function to parse the forecast data according to the specifications in the PDF
def parse_forecast(df):
    # Add any specific parsing logic based on the PDF specification here.
    # This is an example based on a general understanding of CSV data.
    return df

# Streamlit app
st.title("Airport Weather Forecast")

# Input field for ICAO code
icao_code = st.text_input("Enter ICAO code:").lower()

if icao_code:
    with st.spinner('Fetching latest forecast...'):
        base_url = "https://data.dwd.de/aviation/ATM/AirportWxForecast"
        file_content = find_latest_file(base_url, icao_code)
        
        if file_content:
            st.success("Forecast data fetched successfully!")
            
            # Decode the forecast data
            try:
                df = decode_forecast(file_content)
                df = parse_forecast(df)  # Apply any specific parsing logic
                
                # Display the forecast data
                st.dataframe(df)
            except (UnicodeDecodeError, ValueError) as e:
                st.error(f"Failed to decode the forecast data: {e}")
        else:
            st.error(f"No forecast file found for ICAO code: {icao_code}")
