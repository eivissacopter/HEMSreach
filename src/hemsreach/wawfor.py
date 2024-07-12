import streamlit as st
import requests
from bs4 import BeautifulSoup
import pygrib
import pandas as pd
import folium
from streamlit_folium import folium_static
import os
from datetime import datetime, timedelta

# Load secrets from Streamlit
data_server = st.secrets["data_server"]

# Function to fetch the latest file from the directory with authentication
def fetch_latest_file(base_url):
    try:
        response = requests.get(base_url, auth=(data_server["user"], data_server["password"]))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.grb2')]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            file_url = base_url + latest_file
            st.write(f"Latest file URL: {file_url}")
            response = requests.get(file_url, auth=(data_server["user"], data_server["password"]))
            if response.status_code == 200:
                file_path = os.path.join("/tmp", latest_file)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return file_path
            else:
                st.error(f"Failed to download the file: {response.status_code}")
                st.error(f"Response content: {response.content}")
        else:
            st.error("No .grb2 files found in the directory listing.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching latest file: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
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
                timestamp = grb.validDate

                for i in range(data.shape[0]):
                    for j in range(data.shape[1]):
                        if data[i, j] > 0:
                            icing_data.append({
                                'latitude': lat[i, j],
                                'longitude': lon[i, j],
                                'level': levels,
                                'severity': data[i, j],
                                'time': timestamp
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

# Function to create a map with icing data
def create_icing_map(df):
    icing_map = folium.Map(location=[50, 10], zoom_start=4)
    severity_colors = {'Light': 'blue', 'Moderate': 'orange', 'Severe': 'red'}

    for _, row in df.iterrows():
        folium.CircleMarker(
            location=(row['latitude'], row['longitude']),
            radius=5,
            color=severity_colors.get(row['severity'], 'black'),
            fill=True,
            fill_color=severity_colors.get(row['severity'], 'black'),
            fill_opacity=0.7,
            popup=f"Level: {row['level']}<br>Severity: {row['severity']}<br>Time: {row['time']}"
        ).add_to(icing_map)

    return icing_map

# Streamlit app layout
st.title("Aviation Icing Hazard Data")

base_url = "https://data.dwd.de/aviation/WAWFOR/data_set_ice/IconEU/"

if st.button('Fetch Latest Icing Data'):
    st.info("Fetching the latest file...")
    latest_file = fetch_latest_file(base_url)
    if latest_file:
        st.success(f"Downloaded the latest file: {latest_file}")
        st.info("Decoding the file...")
        icing_df = decode_grib2(latest_file)
        if icing_df is not None:
            st.info("Analyzing icing data...")
            icing_summary = analyze_icing(icing_df)
            if icing_summary is not None:
                st.subheader("Icing Hazard Summary")
                st.dataframe(icing_summary)

                st.subheader("Icing Hazard Map")
                icing_map = create_icing_map(icing_df)
                folium_static(icing_map)

                st.subheader("Check Icing Hazard on Your Route")
                start_lat = st.number_input("Enter Start Latitude", format="%.6f")
                start_lon = st.number_input("Enter Start Longitude", format="%.6f")
                end_lat = st.number_input("Enter End Latitude", format="%.6f")
                end_lon = st.number_input("Enter End Longitude", format="%.6f")
                altitude = st.number_input("Enter Altitude (level)", format="%.1f")
                hours_ahead = st.number_input("Enter Hours Ahead", min_value=0, max_value=24, value=5)
                check_button = st.button("Check Icing Hazard")

                if check_button:
                    current_time = datetime.utcnow()
                    end_time = current_time + timedelta(hours=hours_ahead)
                    route_icing = icing_df[
                        (icing_df['time'] >= current_time) &
                        (icing_df['time'] <= end_time) &
                        (icing_df['level'] == altitude) &
                        ((icing_df['latitude'] >= min(start_lat, end_lat)) & (icing_df['latitude'] <= max(start_lat, end_lat))) &
                        ((icing_df['longitude'] >= min(start_lon, end_lon)) & (icing_df['longitude'] <= max(start_lon, end_lon)))
                    ]
                    if not route_icing.empty:
                        st.write(f"Icing hazards detected along the route:")
                        st.dataframe(route_icing[['latitude', 'longitude', 'level', 'severity', 'time']])
                    else:
                        st.write("No icing hazards detected along this route and altitude within the specified time frame.")
            else:
                st.warning("No icing data found.")
        else:
            st.error("Failed to decode the GRIB2 file.")
    else:
        st.error("Failed to download the latest GRIB2 file.")
else:
    st.info("Click the button to fetch the latest icing data.")
