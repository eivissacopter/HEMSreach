import streamlit as st
import datetime
import re

def decode_metar(metar):
    metar = re.sub(r'[\r\n]+', ' ', metar).strip()  # Remove \r and \n characters
    parts = metar.split()
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
    taf = re.sub(r'[\r\n]+', ' ', taf).strip()  # Remove \r and \n characters
    parts = taf.split()
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

def parse_trends(remarks):
    trends = re.findall(r'(BECMG|TEMPO|FM|TL|AT|PROB\d{2})\s+\d{4}/\d{4}\s+.*?(?=(BECMG|TEMPO|FM|TL|AT|PROB\d{2}|\s*$))', remarks)
    parsed_trends = []
    for trend in trends:
        parsed_trends.append(trend[0] + ' ' + trend[1].strip())
    return parsed_trends

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

    # Parse trends in METAR remarks
    trends = parse_trends(metar_data['Remarks'])

    # Create a timeline of weather changes
    timeline = []

    # Add METAR trends to timeline
    for trend in trends:
        trend_type, trend_info = trend.split(maxsplit=1)
        if trend_type == 'BECMG':
            trend_start, trend_end, trend_details = trend_info.split(maxsplit=2)
            trend_start_time = datetime.datetime.strptime(trend_start, '%d%H%M')
            trend_end_time = datetime.datetime.strptime(trend_end, '%d%H%M')
            timeline.append((trend_start_time, trend_end_time, trend_details))

    # Add TAF changes to timeline
    taf_changes = taf_data['Changes'].split()
    for i in range(0, len(taf_changes), 5):
        change_time = taf_changes[i]
        change_type = taf_changes[i + 1]
        change_details = ' '.join(taf_changes[i + 2:i + 5])
        if re.match(r'^\d{4}/\d{4}$', change_time):
            change_start_time = datetime.datetime.strptime(change_time[:4] + "00", '%d%H%M')
            change_end_time = datetime.datetime.strptime(change_time[5:] + "00", '%d%H%M')
            timeline.append((change_start_time, change_end_time, change_details))

    # Sort timeline by start time
    timeline.sort(key=lambda x: x[0])

    lowest_visibility = 9999
    lowest_cloud_base = 9999

    # Evaluate timeline to find lowest visibility and cloud base in the specified hours ahead
    for start, end, details in timeline:
        if current_time <= start <= future_time:
            if 'CAVOK' in details:
                visibility = 9999
                cloud_base = 9999
            else:
                try:
                    visibility = int(re.sub("[^0-9]", "", details.split()[0]))
                    cloud_base = int(re.sub("[^0-9]", "", details.split()[1]))
                except ValueError:
                    visibility = 9999
                    cloud_base = 9999
            lowest_visibility = min(lowest_visibility, visibility)
            lowest_cloud_base = min(lowest_cloud_base, cloud_base)

    # Add current METAR to timeline
    if current_time <= metar_time <= future_time:
        if 'CAVOK' in metar_data['Clouds']:
            visibility_metar = 9999
            cloud_base_metar = 9999
        else:
            try:
                visibility_metar = int(re.sub("[^0-9]", "", metar_data['Visibility']))
                cloud_base_metar = int(re.sub("[^0-9]", "", metar_data['Clouds'][3:6]))
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
