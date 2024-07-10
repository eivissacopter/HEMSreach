import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from datetime import datetime, timedelta
from database import helicopter_bases, airports

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

def parse_forecast(df):
    return df

def find_closest_airport_with_forecast(base_lat, base_lon, available_icao_codes):
    sorted_airports = sorted(airports, key=lambda airport: geodesic((base_lat, base_lon), (airport['lat'], airport['lon'])).kilometers)
    for airport in sorted_airports:
        if airport['icao'].lower() in available_icao_codes:
            return airport
    return None

def extract_icao_codes(directory_listing):
    soup = BeautifulSoup(directory_listing, 'html.parser')
    icao_codes = [a['href'].strip('/').lower() for a in soup.find_all('a', href=True) if len(a['href'].strip('/')) == 4]
    return icao_codes

def get_wind_at_altitude(location):
    base_url = "https://data.dwd.de/aviation/ATM/AirportWxForecast"
    directory_listing = fetch_directory_listing(base_url)
    
    if directory_listing:
        available_icao_codes = set(extract_icao_codes(directory_listing))
        closest_airport = find_closest_airport_with_forecast(location['lat'], location['lon'], available_icao_codes)
        
        if closest_airport:
            file_content = find_latest_file(base_url, closest_airport['icao'])
            
            if file_content:
                try:
                    df = decode_forecast(file_content, closest_airport['icao'])
                    df = parse_forecast(df)

                    df.columns = [f"{closest_airport['icao'].upper()}{i:02d}" for i in range(len(df.columns))]
                    relevant_rows = ['UTC', '5000FT', 'FZLVL']
                    df_relevant = df[df.iloc[:, 0].isin(relevant_rows)]

                    if df_relevant.empty:
                        return {"error": "Relevant rows (UTC, 5000FT, FZLVL) not found in dataframe."}
                    else:
                        df_converted = pd.DataFrame()

                        if 'UTC' in df_relevant.iloc[:, 0].values:
                            df_converted['UTC'] = pd.to_numeric(df_relevant.loc[df_relevant.iloc[:, 0] == 'UTC'].iloc[0, 1:], errors='coerce').dropna().apply(lambda x: f"{int(x):02d}:00")

                        if '5000FT' in df_relevant.iloc[:, 0].values:
                            df_5000FT = df_relevant.loc[df_relevant.iloc[:, 0] == '5000FT'].iloc[0, 1:]
                            df_converted['WD@5000FT'] = df_5000FT.apply(lambda x: round(float(x.split(' ')[0].split('/')[0])) if '/' in x and x.split(' ')[0].split('/')[0].isdigit() else None)
                            df_converted['WS@5000FT'] = df_5000FT.apply(lambda x: round(float(x.split(' ')[0].split('/')[1])) if '/' in x and x.split(' ')[0].split('/')[1].isdigit() else None)

                        if 'FZLVL' in df_relevant.iloc[:, 0].values:
                            df_converted['FZLVL'] = df_relevant.loc[df_relevant.iloc[:, 0] == 'FZLVL'].iloc[0, 1:].dropna().apply(lambda x: int(float(x) * 100) if x.replace('.', '', 1).isdigit() else None)

                        avg_wd_5000ft = df_converted['WD@5000FT'].dropna().astype(float).mean()
                        avg_ws_5000ft = df_converted['WS@5000FT'].dropna().astype(float).mean()
                        lowest_fzlv = df_converted['FZLVL'].dropna().astype(float).min()
                        
                        return {
                            'closest_airport': closest_airport,
                            'wind_direction': round(avg_wd_5000ft) if not pd.isna(avg_wd_5000ft) else None,
                            'wind_speed': round(avg_ws_5000ft) if not pd.isna(avg_ws_5000ft) else None,
                            'freezing_level': int(lowest_fzlv) if not pd.isna(lowest_fzlv) else None
                        }

                except (UnicodeDecodeError, ValueError, KeyError, IndexError) as e:
                    return {"error": f"Failed to decode or process the forecast data for {closest_airport['name']} ({closest_airport['icao']}): {e}"}
            else:
                return {"error": f"No forecast file found for airport: {closest_airport['name']} ({closest_airport['icao']})."}
        else:
            return {"error": "No closest airport found with available forecast data."}
    else:
        return {"error": "Failed to fetch the directory listing."}
