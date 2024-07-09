import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from database import helicopter_bases, airports
import os

# Function to fetch file content via HTTPS
def fetch_file_content(url):
    try:
        response = requests.get(url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error fetching data from URL: {url} - Error: {e}")
        return None

# Function to find the latest available file by scanning the directory
def find_latest_file(base_url, icao_code):
    try:
        url = f"{base_url}/{icao_code.lower()}/"
        response = requests.get(url, auth=(st.secrets["data_server"]["user"], st.secrets["data_server"]["password"]))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if f"airport_forecast_{icao_code.lower()}_" in a['href']]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            return fetch_file_content(f"{base_url}/{icao_code.lower()}/{latest_file}")
        else:
            st.warning(f"No forecast file found for ICAO code: {icao_code}.")
            return None
    except Exception as e:
        st.error(f"Error fetching directory listing or file content for ICAO code: {icao_code} - Error: {e}")
        return None

# Function to decode and process forecast data
def process_forecast_data(file_content, forecast_hour):
    try:
        df = pd.read_fwf(pd.compat.StringIO(file_content.decode('utf-8')))
        df.columns = df.iloc[0]
        df = df[1:]

        required_columns = ['WD@5000FT', 'WS@5000FT', 'FZLVL']
        if not all(col in df.columns for col in required_columns):
            st.error("Required columns not found in data.")
            return None

        df = df.apply(pd.to_numeric, errors='coerce')
        avg_wd_5000ft = df['WD@5000FT'][:forecast_hour].mean()
        avg_ws_5000ft = df['WS@5000FT'][:forecast_hour].mean()
        lowest_fzlv = df['FZLVL'][:forecast_hour].min()

        return avg_wd_5000ft, avg_ws_5000ft, lowest_fzlv
    except Exception as e:
        st.error(f"Error processing forecast data: {e}")
        return None

# Main function to run the Streamlit app
def main():
    base_url = st.secrets.get("data_server", {}).get("server", os.getenv("DEFAULT_BASE_URL"))
    if not base_url:
        st.error("Base URL is not configured. Please check the secrets configuration.")
        return
    
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    
    st.title("Airport Weather Forecast")

    selected_airport = st.selectbox("Select Airport", airports)
    forecast_hour = st.slider("Select Forecast Hour", 1, 24, 12)

    if st.button("Get Forecast"):
        file_content = find_latest_file(base_url, selected_airport['icao'])
        if file_content:
            result = process_forecast_data(file_content, forecast_hour)
            if result:
                avg_wd_5000ft, avg_ws_5000ft, lowest_fzlv = result
                st.write(f"Average WD@5000FT: {avg_wd_5000ft:.2f}")
                st.write(f"Average WS@5000FT: {avg_ws_5000ft:.2f}")
                st.write(f"Lowest FZLVL: {lowest_fzlv:.2f}")

if __name__ == "__main__":
    main()
