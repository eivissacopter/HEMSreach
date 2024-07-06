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
        'Weather': parts[4],
        'Clouds': parts[5],
        'Temperature/Dewpoint': parts[6],
        'QNH': parts[7],
        'Remarks': ' '.join(parts[8:])
    }
    return data

def decode_taf(taf):
    parts = taf.replace('\r', '').replace('\n', ' ').split()
    validity_index = next(i for i, part in enumerate(parts) if '/' in part)
    data = {
        'ICAO': parts[0],
        'Time': parts[1],
        'Validity': parts[validity_index],
        'Wind': parts[validity_index + 1],
        'Visibility': parts[validity_index + 2],
        'Weather': parts[validity_index + 3],
        'Clouds': parts[validity_index + 4],
        'Changes': ' '.join(parts[validity_index + 5:])
    }
    return data

def parse_validity(validity):
    taf_start = validity[:4] + "00"
    taf_end = validity[5:] + "00"
    try:
        taf_start_time = datetime.datetime.strptime(taf_start, '%d%H%M')
        taf_end_time = datetime.datetime.strptime(taf_end, '%d%H%M')
        return taf_start_time, taf_end_time
    except ValueError as e:
        raise ValueError(f"Error parsing TAF validity times: {e}")

def analyze_weather(metar, taf, hours_ahead):
    metar_data = decode_metar(metar)
    taf_data = decode_taf(taf)

    current_time = datetime.datetime.utcnow()
    metar_time = datetime.datetime.strptime(metar_data['Time'], '%d%H%MZ')
    future_time = current_time + datetime.timedelta(hours=hours_ahead)

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
        visibility_metar = 9999 if metar_data['Visibility'] == 'CAVOK' else int(re.sub("[^0-9]", "", metar_data['Visibility']))
        visibility_taf = 9999 if taf_data['Visibility'] == 'CAVOK' else int(re.sub("[^0-9]", "", taf_data['Visibility']))
        lowest_visibility = min(visibility_metar, visibility_taf)
        
        cloud_base_metar = 9999 if 'CAVOK' in metar_data['Clouds'] else int(re.sub("[^0-9]", "", metar_data['Clouds'][3:6]))
        cloud_base_taf = 9999 if 'CAVOK' in taf_data['Clouds'] else int(re.sub("[^0-9]", "", taf_data['Clouds'][3:6]))
        lowest_cloud_base = min(cloud_base_metar, cloud_base_taf)
    except ValueError as e:
        st.error(f"Error parsing visibility or cloud base: {e}")
        return metar_data, taf_data, None, None, ["Invalid visibility or cloud base values"]

    # Compare METAR and TAF forecasts within the specified hours ahead
    if metar_time < future_time:
        visibility_ahead = visibility_metar
        cloud_base_ahead = cloud_base_metar
    else:
        visibility_ahead = 9999
        cloud_base_ahead = 9999

    if taf_start_time < future_time < taf_end_time:
        visibility_ahead = min(visibility_ahead, visibility_taf)
        cloud_base_ahead = min(cloud_base_ahead, cloud_base_taf)

    return metar_data, taf_data, visibility_ahead, cloud_base_ahead, warnings

st.title("METAR/TAF Decoder")

metar = st.text_area("Enter METAR:")
taf = st.text_area("Enter TAF:")
hours_ahead = st.slider("Hours Ahead", 0, 9, 5)

if st.button("Submit"):
    if metar and taf:
        metar_data, taf_data, visibility, cloud_base, warnings = analyze_weather(metar, taf, hours_ahead)

        st.subheader("Decoded METAR")
        st.json(metar_data)

        st.subheader("Decoded TAF")
        st.json(taf_data)

        st.subheader("Analysis")
        if visibility is not None and cloud_base is not None:
            st.write(f"Lowest Visibility in next {hours_ahead} hours: {visibility} meters")
            st.write(f"Lowest Cloud Base in next {hours_ahead} hours: {cloud_base} feet")
        st.write("Warnings:")
        for warning in warnings:
            st.write(f"- {warning}")
    else:
        st.warning("Please enter both METAR and TAF.")
