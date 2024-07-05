import paramiko
import pandas as pd
import streamlit as st
from datetime import datetime
import io

# Load secrets
data_server = st.secrets["data_server"]

# List of airports based on the document structure
airports = ["EDDB", "EDDC", "EDDE", "EDDF", "EDDG", "EDDH", "EDDK", 
            "EDDL", "EDDM", "EDDN", "EDDP", "EDDR", "EDDS", "EDDV", "EDDW"]

# Function to fetch METAR data via SFTP
def fetch_metar_data_sftp(airport):
    try:
        hostname = data_server["server"]
        port = int(data_server["port"])  # Ensure the port is an integer
        username = data_server["user"]
        password = data_server["password"]
        
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # List the files in the airport's METAR_SPECI directory and get the most recent file
        directory_path = f'/aviation/ACT/{airport}/METAR_SPECI/'  # Adjust the path as needed
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

# Function to extract METAR report from file content
def extract_metar_report(file_content):
    try:
        # Decode the content and split by lines
        lines = file_content.decode('utf-8').strip().split('\n')
        # Assuming the METAR report is on the fourth line
        metar_report = lines[3]
        return metar_report
    except:
        return None

# Streamlit setup
st.title("Latest METARs Viewer")

# Fetch and display the latest METAR data for each airport
metar_data = []

for airport in airports:
    file_content = fetch_metar_data_sftp(airport)
    if file_content:
        metar_report = extract_metar_report(file_content)
        if metar_report:
            metar_data.append((airport, metar_report))

# Display the collected METAR data
if metar_data:
    st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for airport, metar in metar_data:
        st.write(f"{airport}: {metar}")
