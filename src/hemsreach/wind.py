import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from datetime import datetime, timedelta
from database import helicopter_bases, airports

# Function to fetch directory listing
def fetch_directory_listing(base_url):
    try:
        response = requests.get(base_url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        if response.status_code == 200:
            return response.text
        else:
            st.warning(f"Failed to fetch directory listing from URL: {base_url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching directory listing from URL: {base_url} - Error: {e}")
        return None

# Function to fetch file content via HTTPS
def fetch_file_content(url):
    try:
        response = requests.get(url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        if response.status_code == 200:
            return response.content
        else:
            st.warning(f"Failed to fetch data from URL: {url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from URL: {url} - Error: {e}")
        return None

# Function to find the latest available file by scanning the directory
def find_latest_file(base_url, icao_code):
    directory_listing = fetch_directory_listing(base_url + f"/{icao_code.lower()}/")
    if directory_listing:
        soup = BeautifulSoup(directory_listing, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if f"airport_forecast_{icao_code.lower()}_" in a['href']]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            url = f"{base_url}/{icao_code.lower()}/{latest_file}"
            file_content = fetch_file_content(url)
            return file_content
        else:
            st.warning(f"No forecast files found for {icao_code}.")
    return None

# Function to decode the forecast data
def decode_forecast(data, icao_code):
    for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
        try:
            content = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("All decoding attempts failed.")
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith("DATE;"):
            header_index = i
            break
    else:
        raise ValueError("Header not found in the file.")
    
    data_lines = lines[header_index:]
    rows = [line.split(';') for line in data_lines if len(line.split(';')) > 1]
    num_columns = len(rows[0])
    column_names = [f"{icao_code.upper()}{i:02d}" for i in range(num_columns)]
    df = pd.DataFrame(rows, columns=column_names)
    return df

# Function to parse the forecast data according to the specifications in the PDF
def parse_forecast(df):
    return df

# Function to calculate the closest airport to a given helicopter base
def find_closest_airport_with_forecast(base_lat, base_lon, available_icao_codes):
    sorted_airports = sorted(airports, key=lambda airport: geodesic((base_lat, base_lon), (airport['lat'], airport['lon'])).kilometers)
    for airport in sorted_airports:
        if airport['icao'].lower() in available_icao_codes:
            return airport
    return None

# Function to extract ICAO codes from the directory listing
def extract_icao_codes(directory_listing):
    soup = BeautifulSoup(directory_listing, 'html.parser')
    icao_codes = [a['href'].strip('/').lower() for a in soup.find_all('a', href=True) if len(a['href'].strip('/')) == 4]
    return icao_codes

# Streamlit app
st.title("Airport Weather Forecast")

# Dropdown menu for helicopter bases
base_names = [base['name'] for base in helicopter_bases]
selected_base = st.selectbox("Select a Helicopter Base", base_names)

if selected_base:
    base = next(base for base in helicopter_bases if base['name'] == selected_base)
    
    # Calculate current time and time range for slider
    now = datetime.utcnow()
    local_now = now + timedelta(hours=2)  # Assuming local time is UTC+2
    time_options = [local_now + timedelta(hours=i) for i in range(7)]
    time_labels = [t.strftime("%H:%M") for t in time_options]

    # Time slider for selection
    selected_time = st.slider("Select time window (hours)", min_value=0, max_value=6, value=1)

    with st.spinner('Fetching available ICAO codes...'):
        base_url = "https://data.dwd.de/aviation/ATM/AirportWxForecast"
        directory_listing = fetch_directory_listing(base_url)
        if directory_listing:
            available_icao_codes = set(extract_icao_codes(directory_listing))
            if not available_icao_codes:
                st.error("No ICAO codes found in the directory listing.")
            else:
                closest_airport = find_closest_airport_with_forecast(base['lat'], base['lon'], available_icao_codes)
                if closest_airport:
                    with st.spinner(f'Fetching latest forecast for {closest_airport["name"]} ({closest_airport["icao"]})...'):
                        file_content = find_latest_file(base_url, closest_airport['icao'])
                        if file_content:
                            try:
                                df = decode_forecast(file_content, closest_airport['icao'])
                                df = parse_forecast(df)

                                # Rename columns starting from EDDM00, EDDM01, EDDM02, etc.
                                df.columns = [f"{closest_airport['icao'].upper()}{i:02d}" for i in range(len(df.columns))]

                                # Keep only the relevant rows
                                relevant_rows = ['UTC', '5000FT', 'FZLVL']
                                df_relevant = df[df.iloc[:, 0].isin(relevant_rows)]

                                # Ensure relevant rows exist before processing
                                if df_relevant.empty:
                                    st.error("Relevant rows (UTC, 5000FT, FZLVL) not found in dataframe.")
                                else:
                                    # Convert the relevant rows
                                    df_converted = pd.DataFrame()

                                    if 'UTC' in df_relevant.iloc[:, 0].values:
                                        df_converted['UTC'] = pd.to_numeric(df_relevant.loc[df_relevant.iloc[:, 0] == 'UTC'].iloc[0, 1:], errors='coerce').dropna().apply(lambda x: f"{int(x):02d}:00")
                                    else:
                                        st.error("'UTC' row not found in dataframe.")

                                    if '5000FT' in df_relevant.iloc[:, 0].values:
                                        df_5000FT = df_relevant.loc[df_relevant.iloc[:, 0] == '5000FT'].iloc[0, 1:]
                                        df_converted['WD@5000FT'] = df_5000FT.apply(lambda x: x.split(' ')[0].split('/')[0] if '/' in x else None)
                                        df_converted['WS@5000FT'] = df_5000FT.apply(lambda x: x.split(' ')[0].split('/')[1] if '/' in x else None)
                                    else:
                                        st.error("'5000FT' row not found in dataframe.")

                                    if 'FZLVL' in df_relevant.iloc[:, 0].values:
                                        df_converted['FZLVL'] = df_relevant.loc[df_relevant.iloc[:, 0] == 'FZLVL'].iloc[0, 1:].dropna()
                                    else:
                                        st.error("'FZLVL' row not found in dataframe.")

                                    # Calculate average WD@5000FT, average WS@5000FT, and lowest FZLVL based on slider value
                                    col_prefix = closest_airport['icao'].upper()
                                    col_range = [f"{col_prefix}{i:02d}" for i in range(1, selected_time + 1)]
                                    
                                    avg_wd_5000ft = df_converted['WD@5000FT'][col_range].astype(float).mean()
                                    avg_ws_5000ft = df_converted['WS@5000FT'][col_range].astype(float).mean()
                                    lowest_fzlv = df_converted['FZLVL'][col_range].astype(float).min()
                                    
                                    # Print the results without decimals
                                    st.write(f"Wind Direction: {int(round(avg_wd_5000ft))}")
                                    st.write(f"Wind Speed: {int(round(avg_ws_5000ft))}")
                                    st.write(f"Freezing Level: {int(round(lowest_fzlv))}")

                            except (UnicodeDecodeError, ValueError, KeyError, IndexError) as e:
                                st.error(f"Failed to decode or process the forecast data for {closest_airport['name']} ({closest_airport['icao']}): {e}")
                        else:
                            st.warning(f"No forecast file found for airport: {closest_airport['name']} ({closest_airport['icao']}).")
                else:
                    st.error("No closest airport found with available forecast data.")
        else:
            st.error("Failed to fetch the directory listing.")
