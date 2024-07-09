import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime

# Function to fetch the latest forecast file via HTTPS
def fetch_latest_forecast(icao_code):
    base_url = "https://data.dwd.de/aviation/ATM/AirportWxForecast/"
    response = requests.get(base_url)
    
    if response.status_code != 200:
        return None, f"Failed to access the server: {response.status_code}"
    
    # Parse the directory listing
    files = response.text.split('\n')
    
    # Find the latest file for the specified ICAO code
    latest_file = None
    latest_time = None
    for file in files:
        if icao_code.lower() in file.lower():
            # Extract datetime from the filename
            try:
                dt_str = file.split('_')[-1].split('.')[0]
                file_time = datetime.strptime(dt_str, '%Y%m%d%H%M')
                if latest_time is None or file_time > latest_time:
                    latest_time = file_time
                    latest_file = file
            except ValueError:
                continue
    
    if not latest_file:
        return None, f"No forecast file found for ICAO code: {icao_code}"
    
    # Fetch the latest file
    file_url = base_url + latest_file
    file_response = requests.get(file_url)
    
    if file_response.status_code != 200:
        return None, f"Failed to fetch the forecast file: {file_response.status_code}"
    
    return file_response.text, None

# Function to decode the forecast data
def decode_forecast(data):
    lines = data.split('\n')
    header = lines[0].split(';')
    rows = [line.split(';') for line in lines[1:] if line]
    df = pd.DataFrame(rows, columns=header)
    return df

# Streamlit app
st.title("Airport Weather Forecast")

# Input field for ICAO code
icao_code = st.text_input("Enter ICAO code:")

if icao_code:
    with st.spinner('Fetching latest forecast...'):
        data, error = fetch_latest_forecast(icao_code)
        
        if error:
            st.error(error)
        else:
            st.success("Forecast data fetched successfully!")
            
            # Decode the forecast data
            df = decode_forecast(data)
            
            # Display the forecast data
            st.dataframe(df)
