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
        port = data_server["port"]
        username = data_server["user"]
        password = data_server["password"]
        
        st.write(f"Connecting to {hostname} on port {port} for airport {airport}")
        
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # List the files in the airport's METAR_SPECI directory and get the most recent file
        directory_path = f'/aviation/ACT/{airport}/METAR_SPECI/'  # Adjust the path as needed
        file_list = sftp.listdir(directory_path)
        
        # Assuming files are named in a way that the most recent file is always at the end
        latest_file = sorted(file_list)[-1]
        
       
