import streamlit as st
import datetime
import re

def decode_metar(metar):
    metar = re.sub(r'[\r\n]+', ' ', metar).strip()  # Remove \r and \n characters

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', metar).group(),
        'Time': re.search(r'\d{6}Z', metar).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', metar).group(),
        'Visibility': re.search(r'\b\d{4}\b', metar).group(),
        'Variable Wind': re.search(r'\d{3}V\d{3}', metar).group() if re.search(r'\d{3}V\d{3}', metar) else '',
        'Clouds': ' '.join(re.findall(r'(FEW|SCT|BKN|OVC)\d{3}', metar)),
        'Temperature/Dewpoint': re.search(r'\d{2}/\d{2}', metar).group(),
        'QNH': re.search(r'\bQ\d{4}\b', metar).group(),
        'Trend': ' '.join(re.findall(r'(TEMPO|BECMG|NOSIG) .*?(?= TEMPO| BECMG| NOSIG|$)', metar))
    }

    # Split Temperature and Dewpoint
    temp_dew = data['Temperature/Dewpoint'].split('/')
    data['Temperature'] = temp_dew[0]
    data['Dewpoint'] = temp_dew[1]
    
    return data

def decode_taf(taf):
    taf = re.sub(r'[\r\n]+', ' ', taf).strip()  # Remove \r and \n characters
    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', taf).group(),
        'Time': re.search(r'\d{6}Z', taf).group(),
        'Validity': re.search(r'\d{4}/\d{4}', taf).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', taf).group(),
        'Visibility': re.search(r'\b\d{4}\b', taf).group(),
        'Weather': re.search(r'(-|\+)?[A-Z]{2,4}', taf).group(),
        'Clouds': ' '.join(re.findall(r'(FEW|SCT|BKN|OVC)\d{3}', taf)),
        'Changes': ' '.join(re.findall(r'(TEMPO|BECMG|FM|TL|AT|PROB\d{2}) .*?(?= TEMPO| BECMG| FM| TL| AT| PROB\d{2}|$)', taf))
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

def parse_trends(trends):
    trend_list = []
    trend_patterns = re.findall(r'(TEMPO|BECMG|NOSIG) .*?(?= TEMPO| BECMG| NOSIG|$)', trends)
    for trend in trend_patterns:
        trend_list.append(trend.strip())
    return trend_list

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

    if metar_time < current_time - datetime.timedelta(minutes=30):
        warnings.append('METAR is out of date.')

    if taf_end_time < current_time:
        warnings.append('TAF is out of date.')

    if 'TS' in metar_data['Weather'] or 'TS' in taf_data['Weather']:
        warnings.append('Thunderstorm detected.')

    trends = parse_trends(metar_data['Trend'])

    timeline = []

    for trend in trends:
        trend_type, trend_info = trend.split(maxsplit=1)
        if trend_type == 'TEMPO':
            trend_details = trend_info.strip()
            timeline.append((metar_time, future_time, trend_details))

    taf_changes = taf_data['Changes'].split()
    for change in taf_changes:
        change_type, change_details = change.split(maxsplit=1)
        timeline.append((taf_start_time, taf_end_time, change_details.strip()))

    timeline.sort(key=lambda x: x[0])

    lowest_visibility = 9999
    lowest_cloud_base = 9999

    for start, end, details in timeline:
        if current_time <= start <= future_time:
            if 'CAVOK' in details:
                visibility = 9999
                cloud_base = 9999
            else:
                try:
                    visibility_match = re.search(r'\b\d{4}\b', details)
                    cloud_base_match = re.search(r'\b(FEW|SCT|BKN|OVC)\d{3}\b', details)
                    visibility = int(visibility_match.group()) if visibility_match else 9999
                    cloud_base = int(cloud_base_match.group()[-3:]) * 100 if cloud_base_match else 9999
                except ValueError:
                    visibility = 9999
                    cloud_base = 9999
            lowest_visibility = min(lowest_visibility, visibility)
            lowest_cloud_base = min(lowest_cloud_base, cloud_base)

    if current_time <= metar_time <= future_time:
        if 'CAVOK' in metar_data['Clouds']:
            visibility_metar = 9999
            cloud_base_metar = 9999
        else:
            try:
                visibility_metar = int(metar_data['Visibility'])
                cloud_base_metar = int(metar_data['Clouds'][3:6]) * 100
            except ValueError:
                visibility_metar = 9999
                cloud_base_metar = 9999
        lowest_visibility = min(lowest_visibility, visibility_metar)
        lowest_cloud_base = min(lowest_cloud_base, cloud_base_metar)

    return metar_data, taf_data, lowest_visibility, lowest_cloud_base, warnings

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
