import paramiko
import pandas as pd
import streamlit as st
from datetime import datetime
import io
from owslib.wms import WebMapService

# Load secrets
data_server = st.secrets["data_server"]
geo_server = st.secrets["geo_server"]

# List of airports based on the document structure
airports = ["EDDB", "EDDC", "EDDE", "EDDF", "EDDG", "EDDH", "EDDK", 
            "EDDL", "EDDM", "EDDN", "EDDP", "EDDR", "EDDS", "EDDV", "EDDW"]

# Function to fetch METAR data via SFTP
def fetch_metar_data_sftp(airport):
    transport = paramiko.Transport((data_server["server"], data_server["port"]))
    transport.connect(username=data_server["user"], password=data_server["password"])
    
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # List the files in the airport's METAR_SPECI directory and get the most recent file
    directory_path = f'/aviation/ACT/{airport}/METAR_SPECI/'  # Adjust the path as needed
    file_list = sftp.listdir(directory_path)
    
    # Assuming files are named in a way that the most recent file is always at the end
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
st.title("Latest METARs Viewer")

# Fetch and display the latest METAR data for each airport
metar_data = []

for airport in airports:
    try:
        file_content = fetch_metar_data_sftp(airport)
        df = transform_data_to_dataframe(file_content)
        
        # Assuming each row in the CSV represents a METAR report
        latest_metar = df.iloc[-1]  # Get the most recent METAR
        metar_data.append((airport, latest_metar))
    except Exception as e:
        st.error(f"Error fetching data for {airport}: {e}")

# Display the collected METAR data
if metar_data:
    st.write(f"Data last updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for airport, metar in metar_data:
        st.write(f"{airport}: {metar}")

# Fetch and display map data from DWD WMS server
wms_url = "https://maps.dwd.de/geoserver/dwd/ows?service=WMS&version=1.3.0&request=GetCapabilities"
wms = WebMapService(wms_url)

# List available layers
layers = list(wms.contents)

# Display available layers
st.subheader("Available WMS Layers")
for layer in layers:
    st.write(layer)

# Example of fetching and displaying a specific layer
selected_layer = st.selectbox("Select a layer to display", layers)

if selected_layer:
    img = wms.getmap(
        layers=[selected_layer],
        srs='EPSG:4326',
        bbox=(5.0, 47.0, 15.0, 55.0),  # Bounding box for Germany
        size=(800, 600),
        format='image/png',
        transparent=True
    )

    st.image(img.read(), caption=f"{selected_layer} layer from DWD WMS")

