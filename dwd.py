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

# Function to fetch data via SFTP
def fetch_data_sftp(airport, directory_path):
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

# Function to extract report from file content
def extract_report(file_content, line_number):
    try:
        # Decode the content and split by lines
        lines = file_content.decode('utf-8').strip().split('\n')
        # Assuming the report is on the specified line
        report = lines[line_number]
        return report
    except:
        return None

# Streamlit setup
st.title("Latest METAR and TAF Viewer")

# Fetch and display the latest METAR and TAF data for each airport
data = []

for airport in airports:
    metar_content = fetch_data_sftp(airport, f'/aviation/ACT/{airport}/METAR_SPECI')
    taf_content = fetch_data_sftp(airport, f'/aviation/ATM/AirportWxForecast/{airport}')
    
    metar_report = extract_report(metar_content, 3) if metar_content else "No data"
    taf_report = extract_report(taf_content, 3) if taf_content else "No data"
    
    data.append([airport, metar_report, taf_report])

# Convert the data into a DataFrame
df = pd.DataFrame(data, columns=["Airport", "METAR", "TAF"])

# Display the collected data
st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.dataframe(df)
