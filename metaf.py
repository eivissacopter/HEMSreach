import streamlit as st
import datetime
import re

def decode_metar(metar):
    parts = metar.replace('\r', '').replace('\n', ' ').split()
    data = {
        'ICAO': parts[0],
        'Time': parts[1],
        'Wind': parts[2],
        'Visibility': parts[3],
        'Weather': ' '.join(parts[4:6]),  # Capture possible compound weather
        'Clouds': parts[6] if 'CAVOK' not in parts[6] else 'CAVOK',  # Handle CAVOK
        'Temperature/Dewpoint': parts[7],
        'QNH': parts[8],
        'Remarks': ' '.join(parts[9:])
    }
    return data

def decode_taf(taf):
    parts = taf.replace('\r', '').replace('\n', ' ').split()
    validity_index = next(i for i, part in enumerate(parts) if re.match(r'^\d{4}/\d{4}$', part))
    data = {
        'ICAO': parts[0],
        'Time': parts[1],
        'Validity': parts[validity_index],
        'Wind': parts[validity_index + 1],
        'Visibility': parts[validity_index + 2],
        'Weather': ' '.join(parts[validity_index + 3:validity_index + 5]),  # Capture possible compound weather
        'Clouds': parts[validity_index + 5],
        'Changes': ' '.join(parts[validity_index + 6:])
    }
    return data

def parse_validity(validity):
    try:
        taf_start_day, taf_start_hour = validity[:2], validity[2:4]
        taf_end_day, taf_end_hour = validity[5:7], validity[7:9]
        taf_start_time = datetime.datetime.utcnow().replace(day=int(taf_start_day), hour=int(taf_start_hour), minute=0, second=0, microsecond=0)
        taf_end_time = datetime.datetime.utcnow().replace(day=int(taf_end_day), hour=int(taf_end_hour), minute=0, second=0, microsecond=0)
        return taf_start_time, taf_end_time
    except ValueError as e:
        raise ValueError(f"Error parsing TAF validity times: {e}")

def analyze_weather(metar, taf):
    metar_data = decode_metar(metar)
    taf_data = decode_taf(taf)

    current_time = datetime.datetime.utcnow()
    metar_time = datetime.datetime.strptime(metar_data['Time'], '%d%H%MZ')

    try:
        taf_start_time, taf_end_time = parse_validity(taf_data['Validity'])
    except ValueError as e:
        st.error(e)
        return metar_data, taf_data, None, None, ["Invalid TAF validity times"]

    warnings = []

    if metar_time < current_time - datetime.timedelta(hours=1):
        warnings.append('METAR is out of date.')

    if taf_end_time < current_time:
        warnings.append('TAF is out of date.')

    if 'TS' in metar_data['Weather'] or 'TS' in taf_data['Weather']:
        warnings.append('Thunderstorm detected.')

    try:
        visibility_metar = int(''.join(filter(str.isdigit, metar_data['Visibility'])))
        visibility_taf = int(''.join(filter(str.isdigit, taf_data['Visibility'])))
        lowest_visibility = min(visibility_metar, visibility_taf)
        
        cloud_base_metar = int(''.join(filter(str.isdigit, metar_data['Clouds'][3:6])))
        cloud_base_taf = int(''.join(filter(str.isdigit, taf_data['Clouds'][3:6])))
        lowest_cloud_base = min(cloud_base_metar, cloud_base_taf)
    except ValueError as e:
        st.error(f"Error parsing visibility or cloud base: {e}")
        return metar_data, taf_data, None, None, ["Invalid visibility or cloud base values"]

    return metar_data, taf_data, lowest_visibility, lowest_cloud_base, warnings

st.title("METAR/TAF Decoder")

metar = st.text_area("Enter METAR:")
taf = st.text_area("Enter TAF:")

if st.button("Submit"):
    if metar and taf:
        metar_data, taf_data, visibility, cloud_base, warnings = analyze_weather(metar, taf)

        st.subheader("Decoded METAR")
        st.json(metar_data)

        st.subheader("Decoded TAF")
        st.json(taf_data)

        st.subheader("Analysis")
        if visibility is not None and cloud_base is not None:
            st.write(f"Lowest Visibility: {visibility} meters")
            st.write(f"Lowest Cloud Base: {cloud_base} feet")
        st.write("Warnings:")
        for warning in warnings:
            st.write(f"- {warning}")
    else:
        st.warning("Please enter both METAR and TAF.")
