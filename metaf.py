import streamlit as st
import datetime

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
    taf_start = validity[:6]
    taf_end = validity[7:]
    try:
        taf_start_time = datetime.datetime.strptime(taf_start, '%d%H%M')
        taf_end_time = datetime.datetime.strptime(taf_end, '%d%H%M')
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
        visibility_metar = int(metar_data['Visibility'].rstrip('KM'))
        visibility_taf = int(taf_data['Visibility'].rstrip('KM'))
        lowest_visibility = min(visibility_metar, visibility_taf)
        
        cloud_base_metar = int(metar_data['Clouds'][3:6])
        cloud_base_taf = int(taf_data['Clouds'][3:6])
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
            st.write(f"Lowest Visibility: {visibility}m")
            st.write(f"Lowest Cloud Base: {cloud_base}ft")
        st.write("Warnings:")
        for warning in warnings:
            st.write(f"- {warning}")
    else:
        st.warning("Please enter both METAR and TAF.")
