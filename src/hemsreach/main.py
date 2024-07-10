import streamlit as st
from streamlit_autorefresh import st_autorefresh
import folium
from streamlit_folium import folium_static

from config import set_page_config, apply_custom_css
from sidebar import create_sidebar
from wtaloft import get_wind_at_altitude
from e6b import calculate_reachable_airports
from database.database import helicopter_bases, airports  # Correct path to database

# Set page configuration and custom CSS
set_page_config()
apply_custom_css()

# Auto-refresh every 30 minutes (1800 seconds)
st_autorefresh(interval=1800 * 1000, key="data_refresh")

# Create sidebar and get user inputs
selected_location, total_fuel_kg, cruise_altitude_ft = create_sidebar(helicopter_bases, airports)

# Fetch wind data at altitude
wind_data = get_wind_at_altitude(selected_location)
wind_direction = wind_data['wind_direction']
wind_speed = wind_data['wind_speed']
freezing_level = wind_data['freezing_level']

# Calculate reachable airports
reachable_airports = calculate_reachable_airports(selected_location, wind_direction, wind_speed, total_fuel_kg, cruise_altitude_ft)

# Further usage of reachable airports to print labels on the map and create the table
# ...

# Function to print labels on the map and create the table
# ...
