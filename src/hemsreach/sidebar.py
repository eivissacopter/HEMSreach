import streamlit as st

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

        selected_time = st.slider("Select time window (hours)", min_value=1, max_value=6, value=1)

        show_terrain_layer = st.checkbox("Terrain")
        show_nowcastmix_layer = st.checkbox("NowCastMix")
        show_lightning_layer = st.checkbox("Lightning")

    return selected_location, total_fuel_kg, cruise_altitude_ft, selected_time, show_nowcastmix_layer, show_lightning_layer, show_terrain_layer
