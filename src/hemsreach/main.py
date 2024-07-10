import streamlit as st
from streamlit_autorefresh import st_autorefresh
import folium
from streamlit_folium import folium_static

from config import set_page_config, apply_custom_css
from sidebar import create_sidebar
from wtaloft import get_wind_at_altitude
from e6b import calculate_reachable_airports
from database import helicopter_bases, airports  # Correct import path

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

###########################################################################################

# Create map centered on selected location using custom EPSG3857 tiles
m = folium.Map(
    location=[selected_location['lat'], selected_location['lon']],
    zoom_start=7,
    tiles=None,  # Disable default tiles
    crs='EPSG3857'  # Use EPSG3857 projection
)

# Add custom tile layer
tile_url = "https://nginx.eivissacopter.com/ofma/clip/merged/512/latest/{z}/{x}/{y}.png"
folium.TileLayer(
    tiles=tile_url,
    attr="Custom Tiles",
    name="Custom EPSG3857 Tiles",
    overlay=False,
    control=True
).add_to(m)

# Add GeoJSON layer if selected
if geojson_selected:
    geojson_layer = fetch_geojson_layer(geojson_layer_url)
    if geojson_layer:
        folium.GeoJson(
            geojson_layer,
            name="MRVA Layer",
            control=True
        ).add_to(m)

# Add reachable airports to the map
reachable_airports_data = []
for airport, distance, bearing, ground_speed_kt, time_to_airport_hours in reachable_airports:
    metar_data, taf_data = fetch_metar_taf_data(airport['icao'], AVWX_API_KEY)

    if metar_data and taf_data:
        metar_raw = metar_data if isinstance(metar_data, str) else metar_data.get('raw', '')
        taf_raw = taf_data if isinstance(taf_data, str) else taf_data.get('raw', '')

        # Calculate descent time using destination airport elevation
        airport_elevation_ft = airport.get('elevation', 500)  # Default to 500ft if not available
        descent_time_hours = (cruise_altitude_ft - airport_elevation_ft) / descent_rate_fpm / 60

        # Calculate fuel burn for descent
        descent_fuel_burn = descent_time_hours * descend_performance['fuel_burn_kgph']

        # Recalculate remaining trip fuel after descent
        remaining_trip_fuel_kg = trip_fuel_kg - (climb_fuel_burn + descent_fuel_burn)

        # Calculate cruise time based on remaining fuel
        cruise_time_hours = remaining_trip_fuel_kg / cruise_fuel_burn_rate

        fuel_required = time_to_airport_hours * cruise_fuel_burn_rate

        reachable_airports_data.append({
            "Airport": f"{airport['name']} ({airport['icao']})",
            "METAR": metar_raw,
            "TAF": taf_raw,
            "Distance (NM)": round(distance, 2),
            "Time (hours)": round(time_to_airport_hours, 2),
            "Track (°)": round(bearing, 2),
            "Ground Speed (kt)": round(ground_speed_kt, 2),
            "Fuel Required (kg)": round(fuel_required, 2),
            "lat": airport['lat'],
            "lon": airport['lon']
        })
        
        popup_text = f"{airport['name']} ({airport['icao']})"
        folium.Marker(
            location=[airport['lat'], airport['lon']],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="plane"),
        ).add_to(m)

# Add LayerControl to map
folium.LayerControl().add_to(m)

# Display map
folium_static(m, width=1440, height=720)

###########################################################################################

# Ensure the columns exist before trying to highlight
if reachable_airports_data:
    # Format the data with units and appropriate rounding
    decoded_airports_data = []

    for airport_data in reachable_airports_data:
        distance_nm = f"{airport_data['Distance (NM)']:.2f} NM"
        time_hours = int(airport_data["Time (hours)"])
        time_minutes = int((airport_data["Time (hours)"] - time_hours) * 60)
        time_hhmm = f"{time_hours:02d}:{time_minutes:02d}"
        track_deg = f"{int(airport_data['Track (°)']):03d}°"
        ground_speed_kt = f"{int(airport_data['Ground Speed (kt)']):03d} kt"
        fuel_required_kg = f"{int(airport_data['Fuel Required (kg)'])} kg"

        metar_raw = airport_data["METAR"]
        taf_raw = airport_data["TAF"]
        
        # Add the raw METAR and TAF data directly
        decoded_airports_data.append({
            "Airport": airport_data["Airport"],
            "Distance (NM)": distance_nm,
            "Time (hours)": time_hhmm,
            "Track (°)": track_deg,
            "Ground Speed (kt)": ground_speed_kt,
            "Fuel Required (kg)": fuel_required_kg,
            "METAR": metar_raw,
            "TAF": taf_raw
        })

    df_decoded = pd.DataFrame(decoded_airports_data)

    # Display the table with the raw METAR and TAF data
    st.markdown("### METAR/TAF Data")
    st.markdown(df_decoded.to_html(escape=False), unsafe_allow_html=True)
else:
    df_decoded = pd.DataFrame(columns=["Airport", "Distance (NM)", "Time (hours)", "Track (°)", "Ground Speed (kt)", "Fuel Required (kg)", "METAR", "TAF"])

    # Display the table
    st.markdown("### METAR/TAF Data")
    st.table(df_decoded)
