import streamlit as st
from wtaloft import get_wind_at_altitude
from fuelpolicy import calculate_fuel_policy
import pandas as pd

def create_sidebar(helicopter_bases, airports):
    with st.sidebar:
        base_names = [base['name'] for base in helicopter_bases]
        airport_names = [airport['name'] for airport in airports]

        base_or_airport = st.radio('Select Departure', ['Base', 'Airport'], horizontal=True)

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

        alternate_required = st.checkbox("Alternate Required")
        alternate_fuel = st.number_input("Alternate Fuel (kg)", value=0, step=10) if alternate_required else 0

        selected_time = st.slider("Select time window (hours)", min_value=0, max_value=6, value=1)

        wind_data = get_wind_at_altitude(selected_location, selected_time)
        if 'error' not in wind_data:
            closest_airport = wind_data['closest_airport']
            st.markdown(f"### Closest Airport for Wind Data: {closest_airport['name']} ({closest_airport['icao']})")
            st.markdown(f"**ICAO Code:** {closest_airport['icao']}")
            st.markdown(f"**Wind Direction:** {wind_data['wind_direction']}°")
            st.markdown(f"**Wind Speed:** {wind_data['wind_speed']} knots")
            st.markdown(f"**Freezing Level:** {wind_data['freezing_level']} ft")

        cruise_fuel_burn = 250  # Adjust this value as needed

        with st.expander("Fuel Policy"):
            fuel_data, trip_fuel_kg = calculate_fuel_policy(total_fuel_kg, cruise_fuel_burn, alternate_required, alternate_fuel)
            df_fuel = pd.DataFrame(fuel_data)
            st.table(df_fuel)

    return selected_location, total_fuel_kg, cruise_altitude_ft, selected_time, trip_fuel_kg
