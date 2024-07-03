import streamlit as st
import pandas as pd
import requests
import math
from datetime import datetime, timedelta
from database import helicopter_bases, airports
from performance import H145D2_PERFORMANCE
import folium
from streamlit_folium import folium_static
from metar import Metar
import pytz

# Set the page configuration at the very top
st.set_page_config(layout="wide")

# Custom CSS to make the map full-screen and as the background
st.markdown(
    """
    <style>
    .reportview-container .main .block-container {
        padding: 0;
    }
    .reportview-container .main {
        background: none;
        padding: 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .fullScreenMap {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
    }
    .stSlider {
        height: 100%;
    }
    .stNumberInput, .stTextInput {
        display: inline-block;
        margin-right: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Function to calculate distance and bearing between two points using the Haversine formula
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Earth radius in kilometers
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 0.539957  # Convert to nautical miles

    # Bearing calculation
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360  # Normalize to 0-360 degrees

    return distance, bearing

# Function to get reachable airports within a certain radius
def get_reachable_airports(base_lat, base_lon, flight_time_hours, cruise_speed_kt, wind_speed, wind_direction):
    reachable_airports = []
    for airport in airports:
        distance, bearing = haversine(base_lon, base_lat, airport['lon'], airport['lat'])
        ground_speed_kt = calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, bearing)
        if ground_speed_kt <= 0:
            continue
        time_to_airport_hours = distance / ground_speed_kt
        if time_to_airport_hours <= flight_time_hours:
            reachable_airports.append((airport, distance))
    reachable_airports.sort(key=lambda x: x[1])
    return reachable_airports

# Function to calculate ground speed considering wind
def calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, flight_direction):
    relative_wind_direction = math.radians(flight_direction - wind_direction)
    wind_component = wind_speed * math.cos(relative_wind_direction)
    ground_speed = cruise_speed_kt - wind_component  # Invert the calculation to correctly apply wind impact
    return ground_speed

# Function to fetch METAR and TAF data
def fetch_metar_taf_data(icao):
    base_url = "https://aviationweather.gov/adds/dataserver_current/httpparam"
    params_metar = {
        "dataSource": "metars",
        "requestType": "retrieve",
        "format": "xml",
        "hoursBeforeNow": 5,
        "stationString": icao
    }
    params_taf = {
        "dataSource": "tafs",
        "requestType": "retrieve",
        "format": "xml",
        "hoursBeforeNow": 5,
        "stationString": icao
    }

    response_metar = requests.get(base_url, params=params_metar)
    response_taf = requests.get(base_url, params=params_taf)

    return response_metar.text, response_taf.text

# Function to parse METAR data
def parse_metar_data(metar_data):
    try:
        report = Metar.Metar(metar_data)
        return report
    except Exception as e:
        return None

# Function to parse TAF data
def parse_taf_data(taf_data):
    taf_reports = []
    lines = taf_data.splitlines()
    for line in lines:
        if line.startswith("TAF") or line.startswith("TAF AMD") or line.startswith("TAF COR"):
            taf_reports.append(line)
    return taf_reports

# Function to check if the data is valid for the coming time window
def is_valid_for_time_window(metar_report, taf_reports, time_window_hours):
    current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
    end_time = current_time + timedelta(hours=time_window_hours)

    if metar_report:
        metar_time = metar_report.time.replace(tzinfo=pytz.UTC)
        if metar_time < current_time or metar_time > end_time:
            return False

    for taf in taf_reports:
        taf_time_str = taf.split()[2]
        taf_time = datetime.strptime(taf_time_str, "%y%m%d%H%M").replace(tzinfo=pytz.UTC)
        if taf_time < current_time or taf_time > end_time:
            return False

    return True

# Function to get weather status based on METAR, TREND, and TAF data
def get_weather_status(metar_report, taf_reports, dest_ok_vis, dest_ok_ceiling, alt_ok_vis, alt_ok_ceiling, no_alt_vis, no_alt_ceiling, nvfr_vis, nvfr_ceiling):
    status = "UNKNOWN"
    color = "gray"

    visibilities = []
    ceilings = []

    if metar_report:
        visibilities.append(metar_report.vis.value())
        if metar_report.sky_conditions:
            ceilings.append(metar_report.sky_conditions[0].altitude() * 100)

    for taf in taf_reports:
        taf_parts = taf.split()
        for part in taf_parts:
            if part.endswith("SM"):
                visibilities.append(int(part.rstrip("SM")) * 1609.34)  # Convert statute miles to meters
            if part.startswith("BKN") or part.startswith("OVC"):
                ceilings.append(int(part[3:]) * 100)  # Convert hundreds of feet to feet

    all_vis = visibilities + [10000]  # Default visibility if not available
    all_ceils = ceilings + [0]        # Default ceiling if not available

    if any(vis < dest_ok_vis or ceil > dest_ok_ceiling for vis, ceil in zip(all_vis, all_ceils)):
        status = "DEST OK"
        color = "red"
    elif any(vis < alt_ok_vis or ceil > alt_ok_ceiling for vis, ceil in zip(all_vis, all_ceils)):
        status = "ALT OK"
        color = "yellow"
    elif any(vis < no_alt_vis or ceil > no_alt_ceiling for vis, ceil in zip(all_vis, all_ceils)):
        status = "NO ALT REQ"
        color = "green"
    elif any(vis < nvfr_vis or ceil > nvfr_ceiling for vis, ceil in zip(all_vis, all_ceils)):
        status = "NVFR OK"
        color = "blue"

    return status, color

# Sidebar for base selection and radius filter
with st.sidebar:
    base_names = [base['name'] for base in helicopter_bases]
    default_base = next(base for base in helicopter_bases if base['name'] == 'Christoph 77 Mainz')
    selected_base_name = st.selectbox('Select Home Base', base_names, index=base_names.index(default_base['name']))
    selected_base = next(base for base in helicopter_bases if base['name'] == selected_base_name)
    
    st.markdown("")
    cruise_altitude_ft = st.slider(
        'Cruise Altitude', 
        min_value=3000, max_value=10000, value=5000, step=1000,
        format="%d ft"
    )
    total_fuel_kg = st.slider(
        'Total Fuel Upload', 
        min_value=300, max_value=723, value=500, step=50,
        format="%d kg"
    )

    # Alternate required checkbox and input
    alternate_required = st.checkbox("Alternate Required")
    alternate_fuel = st.number_input("Alternate Fuel (kg)", value=0, step=10) if alternate_required else 0

    # Expandable section for fuel breakdown
    with st.expander("Fuel Policy"):
        system_test_and_air_taxi = 37
        holding_final_reserve = 100
        air_taxi_to_parking = 20

        contingency_fuel = 0.1 * (total_fuel_kg - holding_final_reserve - system_test_and_air_taxi - air_taxi_to_parking)
        trip_fuel_kg = total_fuel_kg - (system_test_and_air_taxi + holding_final_reserve + air_taxi_to_parking + contingency_fuel)

        # 15 minutes fuel calculation if alternate is not required
        if not alternate_required:
            fifteen_min_fuel = H145D2_PERFORMANCE['fuel_burn_kgph'] * 0.25
            trip_fuel_kg -= fifteen_min_fuel
            approach_fuel = 30
        else:
            fifteen_min_fuel = 0
            approach_fuel = 60

        trip_fuel_kg -= (alternate_fuel + approach_fuel)

        fuel_data = {
            "Fuel Policy": ["System Test / Air Taxi", "Trip Fuel", "Final Reserve", "15 Minutes Fuel" if not alternate_required else "Alternate Fuel", "Approach Fuel", "Air Taxi to Parking", "Contingency Fuel"],
            "Fuel (kg)": [system_test_and_air_taxi, round(trip_fuel_kg), holding_final_reserve, round(fifteen_min_fuel) if not alternate_required else round(alternate_fuel), approach_fuel, air_taxi_to_parking, round(contingency_fuel)]
        }
        df_fuel = pd.DataFrame(fuel_data)
        st.table(df_fuel)

    # Expandable section for weather configuration
    with st.expander("Weather Policy"):
        weather_time_window = st.slider('Weather Time Window (hours)', min_value=1, max_value=10, value=5, step=1)

        col1, col2 = st.columns(2)
        with col1:
            dest_ok_vis = st.text_input("DEST OK Vis (m)", "500")
            alt_ok_vis = st.text_input("ALT OK Vis (m)", "900")
            no_alt_vis = st.text_input("NO ALT Vis (m)", "3000")
            nvfr_vis = st.text_input("NVFR OK Vis (m)", "5000")

        with col2:
            dest_ok_ceiling = st.text_input("DEST OK Ceiling (ft)", "200")
            alt_ok_ceiling = st.text_input("ALT OK Ceiling (ft)", "400")
            no_alt_ceiling = st.text_input("NO ALT Ceiling (ft)", "700")
            nvfr_ceiling = st.text_input("NVFR OK Ceiling (ft)", "1500")

    wind_direction = st.text_input("Wind Direction (°)", "360")
    wind_speed = st.text_input("Wind Speed (kt)", "0")
    freezing_level = st.text_input("Freezing Level (ft)", "5000")
    min_vectoring_altitude = st.text_input("Minimum Vectoring Altitude (ft)", "5000")

    wind_direction = float(wind_direction) if wind_direction else 0
    wind_speed = float(wind_speed) if wind_speed else 0
    freezing_level = float(freezing_level) if freezing_level else 5000
    min_vectoring_altitude = float(min_vectoring_altitude) if min_vectoring_altitude else 5000

# Calculate mission radius
fuel_burn_kgph = H145D2_PERFORMANCE['fuel_burn_kgph']
flight_time_hours = trip_fuel_kg / fuel_burn_kgph
cruise_speed_kt = H145D2_PERFORMANCE['cruise_speed_kt']

# Get reachable airports
reachable_airports = get_reachable_airports(selected_base['lat'], selected_base['lon'], flight_time_hours, cruise_speed_kt, wind_speed, wind_direction)

# Create map centered on selected base
m = folium.Map(location=[selected_base['lat'], selected_base['lon']], zoom_start=7)

# Add OpenFlightMap tiles
folium.TileLayer(
    tiles='https://{s}.tile.openflightmaps.org/{z}/{x}/{y}.png',
    attr='&copy; <a href="https://www.openflightmaps.org">OpenFlightMaps</a>',
    name='OpenFlightMaps'
).add_to(m)

# Add selected base to map
folium.Marker(
    location=[selected_base['lat'], selected_base['lon']],
    popup=selected_base_name,
    icon=folium.Icon(color="blue", icon="info-sign"),
).add_to(m)

# Add all airports to map with color indicating reachability and METAR/TAF data in the popup
for airport in airports:
    distance, bearing = haversine(selected_base['lon'], selected_base['lat'], airport['lon'], airport['lat'])
    ground_speed_kt = calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, bearing)
    time_to_airport_hours = distance / ground_speed_kt if ground_speed_kt > 0 else float('inf')

    metar_data, taf_data = fetch_metar_taf_data(airport['icao'])
    metar_report = parse_metar_data(metar_data)
    taf_reports = parse_taf_data(taf_data)

    if metar_report and taf_reports:
        if time_to_airport_hours <= flight_time_hours:
            color = "darkgrey"
        else:
            color = "lightgrey"
    else:
        color = "lightgrey"

    popup_text = f"{airport['name']} ({airport['icao']})\nMETAR: {metar_data}\nTAF: {taf_data}"
    folium.Marker(
        location=[airport['lat'], airport['lon']],
        popup=popup_text,
        icon=folium.Icon(color=color, icon="plane"),
    ).add_to(m)

# Display map
folium_static(m, width=1280, height=800)

# Create table of reachable airports with METAR and TAF data
reachable_airports_data = []
for airport, distance in reachable_airports:
    metar_data, taf_data = fetch_metar_taf_data(airport['icao'])
    metar_report = parse_metar_data(metar_data)
    taf_reports = parse_taf_data(taf_data)

    if metar_report and taf_reports:
        reachable_airports_data.append({
            "Airport": f"{airport['name']} ({airport['icao']})",
            "METAR": metar_data,
            "TAF": taf_data
        })

df_reachable_airports = pd.DataFrame(reachable_airports_data)
st.table(df_reachable_airports)

# Function to highlight METAR and TAF based on visibility and ceiling
def highlight_weather_conditions(text, vis_thresholds, ceil_thresholds):
    for vis, color in vis_thresholds.items():
        text = text.replace(vis, f"<span style='color:{color}'>{vis}</span>")
    for ceil, color in ceil_thresholds.items():
        text = text.replace(ceil, f"<span style='color:{color}'>{ceil}</span>")
    return text

# Highlight visibility and ceiling in the METAR and TAF columns
vis_thresholds = {
    "500": "red", "900": "yellow", "3000": "green", "5000": "blue"
}
ceil_thresholds = {
    "200": "red", "400": "yellow", "700": "green", "1500": "blue"
}

df_reachable_airports['METAR'] = df_reachable_airports['METAR'].apply(lambda x: highlight_weather_conditions(x, vis_thresholds, ceil_thresholds))
df_reachable_airports['TAF'] = df_reachable_airports['TAF'].apply(lambda x: highlight_weather_conditions(x, vis_thresholds, ceil_thresholds))

st.table(df_reachable_airports)
