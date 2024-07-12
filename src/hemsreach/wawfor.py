import streamlit as st
import requests
from bs4 import BeautifulSoup
import pygrib
import pandas as pd

# Function to fetch directory listing
def fetch_directory_listing(base_url):
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching directory listing: {e}")
        return None

# Function to fetch the latest file from the directory
def fetch_latest_file(base_url):
    listing = fetch_directory_listing(base_url)
    if listing:
        soup = BeautifulSoup(listing, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.grib2')]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            file_url = base_url + latest_file
            response = requests.get(file_url)
            with open(latest_file, 'wb') as f:
                f.write(response.content)
            return latest_file
    return None

# Function to decode the GRIB2 file and extract icing hazard data
def decode_grib2(file_path):
    try:
        grbs = pygrib.open(file_path)
        icing_data = []

        for grb in grbs:
            if 'icing' in grb.parameterName.lower():
                data = grb.values
                lat, lon = grb.latlons()
                levels = grb.level

                for i in range(data.shape[0]):
                    for j in range(data.shape[1]):
                        if data[i, j] > 0:
                            icing_data.append({
                                'latitude': lat[i, j],
                                'longitude': lon[i, j],
                                'level': levels,
                                'severity': data[i, j]
                            })

        df = pd.DataFrame(icing_data)
        return df

    except Exception as e:
        st.error(f"Error decoding GRIB2 file: {e}")
        return None

# Function to analyze icing severity
def analyze_icing(df):
    severity_map = {1: 'Light', 2: 'Moderate', 3: 'Severe'}

    if df is not None and not df.empty:
        df['severity'] = df['severity'].apply(lambda x: severity_map.get(int(x), 'Unknown'))
        icing_summary = df.groupby(['level', 'severity']).size().reset_index(name='count')
        return icing_summary
    else:
        return None

# Streamlit app layout
st.title("Aviation Icing Hazard Data")

base_url = "https://data.dwd.de/aviation/WAWFOR/data_set_ice/IconEU/"

if st.button('Fetch Latest Icing Data'):
    latest_file = fetch_latest_file(base_url)
    if latest_file:
        st.success(f"Downloaded the latest file: {latest_file}")
        icing_df = decode_grib2(latest_file)
        icing_summary = analyze_icing(icing_df)
        
        if icing_summary is not None:
            st.subheader("Icing Hazard Summary")
            st.dataframe(icing_summary)
        else:
            st.warning("No icing data found.")
    else:
        st.error("Failed to download the latest GRIB2 file.")
else:
    st.info("Click the button to fetch the latest icing data.")
