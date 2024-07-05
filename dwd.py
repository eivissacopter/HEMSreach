import paramiko
import pandas as pd
import streamlit as st
from datetime import datetime
import io

# Load secrets
data_server = st.secrets["data_server"]

# Single airport for demonstration
airport = "EDDF"

# Function to fetch data via SFTP
def fetch_data_sftp(directory_path):
    try:
        hostname = data_server["server"]
        port = int(data_server["port"])  # Ensure the port is an integer
        username = data_server["user"]
        password = data_server["password"]
        
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # List the files in the specified directory and get the most recent file
        file_list = sftp.listdir(directory_path)
        
        if not file_list:
            return None
        
        # Assuming files are named in a way that the most recent file is always at the end
        latest_file = sorted(file_list)[-1]
        
        file_path = f"{directory_path}/{latest_file}"
        
        with sftp.file(file_path, mode='r') as file:
            file_content = file.read()
        
        sftp.close()
        transport.close()
        
        return file_content
    except:
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

# Streamlit setup
st.title("Weather Forecast for EDDF")

# Fetch and display the weather forecast data for the airport EDDF
directory_path = f'/aviation/ATM/AirportWxForecast/{airport}/'
file_content = fetch_data_sftp(directory_path)

if file_content:
    forecast_df = parse_forecast_data(file_content)
    if forecast_df is not None:
        # Display the collected data
        st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.dataframe(forecast_df)
else:
    st.write("No data available")

