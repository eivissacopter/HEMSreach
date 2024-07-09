import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from database import helicopter_bases, airports

# Function to fetch directory listing
def fetch_directory_listing(base_url):
    st.write("Fetching directory listing...")
    try:
        response = requests.get(base_url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        if response.status_code == 200:
            st.write("Directory listing fetched successfully.")
            return response.text
        else:
            st.warning(f"Failed to fetch directory listing from URL: {base_url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching directory listing from URL: {base_url} - Error: {e}")
        return None

# Function to fetch file content via HTTPS
def fetch_file_content(url):
    st.write(f"Fetching file content from {url}...")
    try:
        response = requests.get(url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        if response.status_code == 200:
            st.write("File content fetched successfully.")
            return response.content
        else:
            st.warning(f"Failed to fetch data from URL: {url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from URL: {url} - Error: {e}")
        return None

# Function to find the latest available file by scanning the directory
def find_latest_file(base_url, icao_code):
    st.write(f"Finding latest file for {icao_code}...")
    directory_listing = fetch_directory_listing(base_url + f"/{icao_code.lower()}/")
    if directory_listing:
        soup = BeautifulSoup(directory_listing, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if f"airport_forecast_{icao_code.lower()}_" in a['href']]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            url = f"{base_url}/{icao_code.lower()}/{latest_file}"
            st.write(f"Latest file URL: {url}")
            file_content = fetch_file_content(url)
            return file_content
        else:
            st.warning(f"No forecast files found for {icao_code}.")
    return None

# Function to decode the forecast data
def decode_forecast(data):
    st.write("Decoding forecast data...")
    # Try multiple encodings
    for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
        try:
            content = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("All decoding attempts failed.")
    
    lines = content.split('\n')
    
    # Skip initial lines that don't match the number of columns
    for i, line in enumerate(lines):
        if line.startswith("DATE;"):
            header_index = i
            break
    else:
        raise ValueError("Header not found in the file.")
    
    data_lines = lines[header_index:]
    rows = [line.split(';') for line in data_lines if len(line.split(';')) > 1]

    # Create dynamic column headers
    num_columns = len(rows[0])
    column_names = [f"EDDF{i+1:02d}" for i in range(num_columns)]
    
    df = pd.DataFrame(rows, columns=column_names)
    return df

# Function to parse the forecast data according to the specifications in the PDF
def parse_forecast(df):
    # Add any specific parsing logic based on the PDF specification here.
    return df

# Function to calculate the closest airport to a given helicopter base
def find_closest_airport_with_forecast(base_lat, base_lon, available_icao_codes):
    st.write("Finding closest airport with forecast...")
    sorted_airports = sorted(airports, key=lambda airport: geodesic((base_lat, base_lon), (airport['lat'], airport['lon'])).kilometers)
    for airport in sorted_airports:
        st.write(f"Checking airport: {airport['name']} ({airport['icao']})")
        if airport['icao'].lower() in available_icao_codes:
            airport_coords = (airport['lat'], airport['lon'])
            base_coords = (base_lat, base_lon)
            distance = geodesic(base_coords, airport_coords).kilometers
            st.write(f"Distance to {airport['name']} ({airport['icao']}): {distance} km")
            return airport
    st.warning("No closest airport found with the available ICAO codes.")
    return None

# Function to extract ICAO codes from the directory listing
def extract_icao_codes(directory_listing):
    st.write("Extracting ICAO codes from directory listing...")
    soup = BeautifulSoup(directory_listing, 'html.parser')
    icao_codes = [a['href'].strip('/').lower() for a in soup.find_all('a', href=True) if len(a['href'].strip('/')) == 4]
    st.write(f"Extracted ICAO codes: {icao_codes}")
    return icao_codes

# Streamlit app
st.title("Airport Weather Forecast")

# Dropdown menu for helicopter bases
base_names = [base['name'] for base in helicopter_bases]
selected_base = st.selectbox("Select a Helicopter Base", base_names)

if selected_base:
    base = next(base for base in helicopter_bases if base['name'] == selected_base)
    st.write(f"Selected base: {base}")
    
    with st.spinner('Fetching available ICAO codes...'):
        base_url = "https://data.dwd.de/aviation/ATM/AirportWxForecast"
        directory_listing = fetch_directory_listing(base_url)
        if directory_listing:
            available_icao_codes = extract_icao_codes(directory_listing)
            
            # Iterate through sorted list of closest airports
            while True:
                closest_airport = find_closest_airport_with_forecast(base['lat'], base['lon'], available_icao_codes)
                
                if closest_airport:
                    st.write(f"Closest airport to {selected_base} with forecast data is {closest_airport['name']} ({closest_airport['icao']})")
                    
                    with st.spinner('Fetching latest forecast...'):
                        file_content = find_latest_file(base_url, closest_airport['icao'])
                        
                        if file_content:
                            st.success("Forecast data fetched successfully!")
                            
                            # Decode the forecast data
                            try:
                                df = decode_forecast(file_content)
                                df = parse_forecast(df)  # Apply any specific parsing logic
                                
                                # Display the forecast data
                                st.dataframe(df)
                                break
                            except (UnicodeDecodeError, ValueError) as e:
                                st.error(f"Failed to decode the forecast data: {e}")
                        else:
                            available_icao_codes.remove(closest_airport['icao'].lower())
                            st.warning(f"No forecast file found for airport: {closest_airport['name']} ({closest_airport['icao']}). Trying next closest airport...")
                else:
                    st.error("No closest airport found with available forecast data.")
                    break
        else:
            st.error("Failed to fetch the directory listing.")
