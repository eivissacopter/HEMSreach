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
        
        st.write(f"Connecting to {hostname} on port {port} for airport {airport}")
        
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # List the files in the airport's METAR_SPECI directory and get the most recent file
        directory_path = f'/aviation/ACT/{airport}/METAR_SPECI/'  # Adjust the path as needed
        file_list = sftp.listdir(directory_path)
        
        if not file_list:
            st.error(f"No files found in directory {directory_path} for {airport}")
            return None
        
        # Assuming files are named in a way that the most recent file is always at the end
        latest_file = sorted(file_list)[-1]
        st.write(f"Latest file for {airport}: {latest_file}")
        
        file_path = f"{directory_path}/{latest_file}"
        
        with sftp.file(file_path, mode='r') as file:
            file_content = file.read()
        
        sftp.close()
        transport.close()
        
        return file_content
    except paramiko.SSHException as e:
        st.error(f"SSH error for {airport}: {e}")
    except paramiko.AuthenticationException as e:
        st.error(f"Authentication error for {airport}: {e}")
    except paramiko.SFTPError as e:
        st.error(f"SFTP error for {airport}: {e}")
    except Exception as e:
        st.error(f"Error fetching data for {airport}: {e}")

# Function to extract METAR report from file content
def extract_metar_report(file_content):
    try:
        # Decode the content and split by lines
        lines = file_content.decode('utf-8').strip().split('\n')
        # Assuming the METAR report is on the fourth line
        metar_report = lines[3]
        return metar_report
    except Exception as e:
        st.error(f"Error extracting METAR report: {e}")
        return None

# Streamlit setup
st.title("Latest METARs Viewer")

# Fetch and display the latest METAR data for each airport
metar_data = []

for airport in airports:
    try:
        file_content = fetch_metar_data_sftp(airport)
        if file_content:
            st.write(f"File content for {airport} received, length: {len(file_content)} bytes")
            metar_report = extract_metar_report(file_content)
            if metar_report:
                metar_data.append((airport, metar_report))
    except Exception as e:
        st.error(f"Error processing data for {airport}: {e}")

# Display the collected METAR data
if metar_data:
    st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for airport, metar in metar_data:
        st.write(f"{airport}: {metar}")

