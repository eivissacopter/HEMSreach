import streamlit as st
import pandas as pd
from ftplib import FTP
from io import StringIO

# Function to fetch the latest forecast file from the FTP server
def fetch_latest_forecast(icao_code):
    ftp_server = st.secrets["data_server"]["server"]
    ftp_user = st.secrets["data_server"]["user"]
    ftp_password = st.secrets["data_server"]["password"]

    ftp = FTP(ftp_server)
    ftp.login(user=ftp_user, passwd=ftp_password)
    
    # Navigate to the directory containing forecast files
    ftp.cwd('/aviation/ATM/AirportWxForecast/')
    
    # List all files in the directory
    files = ftp.nlst()
    
    # Find the latest file for the specified ICAO code
    latest_file = None
    for file in sorted(files, reverse=True):
        if icao_code.lower() in file.lower():
            latest_file = file
            break
    
    if not latest_file:
        return None, f"No forecast file found for ICAO code: {icao_code}"
    
    # Retrieve the latest file
    with StringIO() as sio:
        ftp.retrlines(f'RETR {latest_file}', sio.write)
        sio.seek(0)
        data = sio.getvalue()
    
    ftp.quit()
    
    return data, None

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
