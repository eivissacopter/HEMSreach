import streamlit as st
from wtaloft import get_wind_at_altitude

def create_sidebar(helicopter_bases, airports):
    with st.sidebar:
        base_names = [base['name'] for base in helicopter_bases]
        airport_names = [airport['name'] for airport in airports]

        # Toggle switch to choose between Bases and Airports
        base_or_airport = st.radio('Select Departure', ['Base', 'Airport'], horizontal=True)

        # Input field for selecting base or airport
        if base_or_airport == 'Base':
            selected_base_name = st.selectbox('Select Home Base', base_names)
            selected_location = next(base for base in helicopter_bases if base['name'] == selected_base_name)
        else:
            selected_airport_name = st.selectbox('Select Airport', airport_names)
            selected_location = next(airport for airport in airports if airport['name'] == selected_airport_name)

        selected_base_elevation = selected_location['elevation_ft']

        st.markdown("")
        cruise_altitude_ft = st.slider(
            'Cruise Altitude',
            min_value=3000, max_value=10000, value=5000, step=1000,
            format="%d ft"
        )
        total_fuel_kg = st.slider(
            'Total Fuel Upload',
            min_value=400, max_value=723, value=500, step=50,
            format="%d kg"
        )

        # Time slider for selecting forecast time window
        selected_time = st.slider("Select time window (hours)", min_value=1, max_value=6, value=1)

        # Fetch wind data and closest airport
        wind_data = get_wind_at_altitude(selected_location, selected_time)
        if 'error' not in wind_data:
            closest_airport = wind_data['closest_airport']
            st.markdown(f"### Closest Airport: {closest_airport['name']} ({closest_airport['icao']})")
            st.markdown(f"**ICAO Code:** {closest_airport['icao']}")
            st.markdown(f"**Wind Direction:** {wind_data['wind_direction']}°")
            st.markdown(f"**Wind Speed:** {wind_data['wind_speed']} knots")
            st.markdown(f"**Freezing Level:** {wind_data['freezing_level']} ft")

    return selected_location, total_fuel_kg, cruise_altitude_ft, selected_time
