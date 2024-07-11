import streamlit as st
from streamlit_autorefresh import st_autorefresh
from config import set_page_config, apply_custom_css
from sidebar import create_sidebar
from wtaloft import get_wind_at_altitude
from e6b import get_reachable_airports
from performance import H145D2_PERFORMANCE
from database import helicopter_bases, airports
import folium
from streamlit_folium import folium_static
import pandas as pd
from layer import get_latest_xml_url, fetch_latest_xml, extract_polygons_from_xml, add_polygons_to_map

# Set page configuration and custom CSS
set_page_config()
apply_custom_css()

# Auto-refresh every 30 minutes (1800 seconds)
st_autorefresh(interval=1800 * 1000, key="data_refresh")

# Create sidebar and get user inputs
selected_location, total_fuel_kg, cruise_altitude_ft, selected_time, trip_fuel_kg = create_sidebar(helicopter_bases, airports)

# Fetch wind data at altitude
wind_data = get_wind_at_altitude(selected_location, selected_time)
if 'error' in wind_data:
    st.error(f"Error fetching wind data: {wind_data['error']}")
else:
    # Calculate reachable airports
    reachable_airports = get_reachable_airports(
        selected_location, wind_data, trip_fuel_kg, cruise_altitude_ft, H145D2_PERFORMANCE
    )

    # Initialize map centered on the selected location
    m = folium.Map(location=[selected_location['lat'], selected_location['lon']], zoom_start=7, tiles=None, crs='EPSG3857')

    # Add custom tile layer
    tile_url = "https://nginx.eivissacopter.com/ofma/original/aero/512/latest/{z}/{x}/{y}.png"
    folium.TileLayer(
        tiles=tile_url,
        attr="Custom Tiles",
        name="Openflightmaps Aero",
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add custom tile layer
    tile_url = "https://nginx.eivissacopter.com/ofma/original/merged/512/latest/{z}/{x}/{y}.png"
    folium.TileLayer(
        tiles=tile_url,
        attr="Custom Tiles",
        name="Openflightmaps Terrain",
        overlay=False,
        control=True
    ).add_to(m)

    # Fetch and add polygons from the latest XML
    xml_url = get_latest_xml_url("https://data.dwd.de/aviation/Special_application/NCM-A/")
    xml_data = fetch_latest_xml(xml_url)
    polygons = extract_polygons_from_xml(xml_data)
    add_polygons_to_map(m, polygons)

    reachable_airports_data = []
    airport_locations = []

    for airport, distance, bearing, ground_speed_kt, time_to_airport_hours in reachable_airports:
        metar_raw = "METAR data here"
        taf_raw = "TAF data here"

        popup_text = f"{airport['name']} ({airport['icao']})"
        folium.Marker(
            location=[airport['lat'], airport['lon']],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="plane"),
        ).add_to(m)

        reachable_airports_data.append({
            "Airport": f"{airport['name']} ({airport['icao']})",
            "METAR": metar_raw,
            "TAF": taf_raw,
            "Distance (NM)": round(distance, 2),
            "Time (hours)": round(time_to_airport_hours, 2),
            "Track (°)": round(bearing, 2),
            "Ground Speed (kt)": round(ground_speed_kt, 2),
            "Fuel Required (kg)": round(time_to_airport_hours * H145D2_PERFORMANCE['cruise']['fuel_burn_kgph'], 2),
            "lat": airport['lat'],
            "lon": airport['lon']
        })

        airport_locations.append((airport['lat'], airport['lon']))

    # Fit the map to the bounds of the reachable airports
    if airport_locations:
        bounds = [[min([loc[0] for loc in airport_locations]), min([loc[1] for loc in airport_locations])],
                  [max([loc[0] for loc in airport_locations]), max([loc[1] for loc in airport_locations])]]
        m.fit_bounds(bounds)

    folium.LayerControl().add_to(m)

    folium_static(m, width=1440, height=720)

    if reachable_airports_data:
        df_decoded = pd.DataFrame(reachable_airports_data)
        st.markdown("### Reachable Airports with METAR/TAF Data")
        st.markdown(df_decoded.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.markdown("### No reachable airports found.")
