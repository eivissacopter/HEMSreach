import paramiko
import pandas as pd
import streamlit as st
import time
from datetime import datetime
import io

# Load secrets
data_server = st.secrets["data_server"]
geo_server = st.secrets["geo_server"]

# Function to fetch weather data via SFTP
def fetch_weather_data_sftp():
    transport = paramiko.Transport((data_server["server"], data_server["port"]))
    transport.connect(username=data_server["user"], password=data_server["password"])
    
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # List the files in the directory and get the most recent file
    directory_path = '/aviation/ACT/'  # Adjust the path as needed
    file_list = sftp.listdir(directory_path)
    
    # Assuming files are named in a way that most recent file is always at the end
    latest_file = sorted(file_list)[-1]
    
    file_path = f"{directory_path}/{latest_file}"
    
    with sftp.file(file_path, mode='r') as file:
        file_content = file.read()
    
    sftp.close()
    transport.close()
    
    return file_content

# Function to transform data into a DataFrame
def transform_data_to_dataframe(file_content):
    # Example: assuming the file content is CSV data
    df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
    return df

# Streamlit setup
st.title("Weather Data Viewer")

# Main loop to update data every 30 minutes
while True:
    # Fetch and transform data
    try:
        file_content = fetch_weather_data_sftp()
        df = transform_data_to_dataframe(file_content)

        # Display the data in Streamlit
        st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error fetching data: {e}")

    # Sleep for 30 minutes
    time.sleep(1800)
