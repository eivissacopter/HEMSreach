import streamlit as st
import datetime
import re

def convert_qnh(qnh):
    """Convert QNH from inches of mercury (A) to hectopascals (Q)."""
    if qnh.startswith('A'):
        inches = int(qnh[1:]) / 100
        hpa = round(inches * 33.8639)
        return f"Q{hpa}"
    return qnh

def decode_metar(metar):
    metar = re.sub(r'[\r\n]+', ' ', metar).strip()  # Remove \r and \n characters

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', metar).group(),
        'Day': re.search(r'\d{2}(?=\d{4}Z)', metar).group(),
        'Time': re.search(r'\d{6}Z', metar).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', metar).group(),
        'Visibility': '9999' if 'CAVOK' in metar else re.search(r'\b\d{4}\b', metar).group(),
        'Variable Wind': re.search(r'\d{3}V\d{3}', metar).group() if re.search(r'\d{3}V\d{3}', metar) else '',
        'QNH': convert_qnh(re.search(r'\b(A\d{4}|Q\d{4})\b', metar).group()) if re.search(r'\b(A\d{4}|Q\d{4})\b', metar) else 'Missing!',
        'Trend': re.search(r'(TEMPO|BECMG|NOSIG)', metar).group() if re.search(r'(TEMPO|BECMG|NOSIG)', metar) else '',
        'Trend Details': re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar).group(2) if re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar) else '',
        'Warnings': []
    }

    cloud_details = []
    if 'CAVOK' in metar:
        cloud_details.append(['CAVOK', ''])
    else:
        clouds = re.findall(r'(FEW|SCT|BKN|OVC)\d{3}', metar)
        for cloud in clouds:
            cloud_type = cloud[:3]
            altitude = cloud[3:]
            cloud_details.append([cloud_type, altitude])

    data['Cloud Details'] = cloud_details
    
    temp_dew = re.search(r'\d{2}/\d{2}', metar)
    if temp_dew:
        temp_dew_split = temp_dew.group().split('/')
        data['Temperature'] = temp_dew_split[0]
        data['Dewpoint'] = temp_dew_split[1]
        data['Spread'] = str(int(data['Temperature']) - int(data['Dewpoint']))

    # Detect warnings
    warnings_patterns = {
        'MI': 'Shallow',
        'BC': 'Patches',
        'PR': 'Partial',
        'DR': 'Drifting',
        'BL': 'Blowing',
        'SH': 'Showers',
        'TS': 'Thunderstorm',
        'FZ': 'Freezing',
        'DZ': 'Drizzle',
        'RA': 'Rain',
        'SN': 'Snow',
        'SG': 'Snow grains',
        'IC': 'Ice crystals',
        'PL': 'Ice pellets',
        'GR': 'Hail',
        'GS': 'Small hail / snow pellets',
        'UP': 'Unknown',
        'BR': 'Mist (visibility > 1000 m)',
        'FG': 'Fog (visibility < 1000 m)',
        'FU': 'Smoke',
        'VA': 'Volcanic ash',
        'DU': 'Widespread dust',
        'SA': 'Sand',
        'HZ': 'Haze',
        'PY': 'Spray',
        'PO': 'Well developed dust/sand whirls',
        'SQ': 'Squall',
        'FC': 'Funnel cloud',
        '+FC': 'Tornado / water spout',
        'SS': 'Sandstorm',
        'DS': 'Dust storm'
    }
    
    for code, description in warnings_patterns.items():
        if code in metar:
            data['Warnings'].append(description)
    
    data['Warnings'] = ', '.join(data['Warnings']) if data['Warnings'] else ''

    return data

def decode_taf(taf):
    taf = re.sub(r'[\r\n]+', ' ', taf).strip()  # Remove \r and \n characters

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', taf).group(),
        'Time': re.search(r'\d{6}Z', taf).group(),
        'Validity': re.search(r'\d{4}/\d{4}', taf).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', taf).group(),
        'Visibility': re.search(r'\b\d{4}\b', taf).group(),
        'Clouds': re.findall(r'(FEW|SCT|BKN|OVC)\d{3}', taf),
        'Changes': re.findall(r'(TEMPO|BECMG|FM|TL|AT|PROB\d{2}) .*?(?= TEMPO| BECMG| FM| TL| AT| PROB\d{2}|$)', taf)
    }

    return data

def format_metar(data):
    time_utc = datetime.datetime.strptime(data['Time'], '%d%H%MZ')
    time_local_start = time_utc + datetime.timedelta(hours=2)  # Assuming local time is UTC+2
    if data['Trend'] != '':
        time_local_end = time_local_start + datetime.timedelta(hours=2)
    else:
        time_local_end = time_local_start + datetime.timedelta(minutes=30)

    formatted_data = {
        "ICAO": data["ICAO"],
        "Day": data["Day"],
        "Start Time": time_local_start.strftime('%H:%M'),
        "End Time": time_local_end.strftime('%H:%M'),
        "Wind Direction": data["Wind"][:3],
        "Wind Speed": data["Wind"][3:5],
        "Wind Gust": data["Wind"][7:9] if 'G' in data["Wind"] else '',
        "Variable": f"{data['Variable Wind'][:3]} - {data['Variable Wind'][4:]}" if data['Variable Wind'] != '' else "",
        "Visibility": f"{data['Visibility']}",
        "Temperature": f"{data['Temperature']}",
        "Dewpoint": f"{data['Dewpoint']}",
        "Spread": f"{data['Spread']}",
        "QNH": f"{data['QNH'][1:]}" if data['QNH'] != 'Missing!' else 'Missing!',
        "Trend Duration": data['Trend'].capitalize() if data['Trend'] != '' else '',
        "Trend Change": data['Trend Details'] if data['Trend Details'] != '' else '',
        "Warnings": data['Warnings']
    }

    return formatted_data

def format_cloud_details(cloud_details):
    cloud_rows = []
    for i, detail in enumerate(cloud_details):
        cloud_rows.append([f"Cloud {i+1} Type", detail[0]])
        cloud_rows.append([f"Cloud {i+1} Altitude", detail[1]])
    return cloud_rows

def format_taf(data):
    formatted_data = {
        "ICAO": data["ICAO"],
        "Time": data["Time"],
        "Validity": data["Validity"],
        "Wind": data["Wind"],
        "Visibility": f"{data['Visibility']}m",
        "Clouds": ', '.join([cloud[:3].capitalize() for cloud in data['Clouds']]) if data['Clouds'] else "CAVOK",
        "Changes": ' | '.join(data['Changes']) if data['Changes'] else ''
    }

    return formatted_data

st.title("METAR/TAF Decoder")

metar = st.text_area("Enter METAR:")
taf = st.text_area("Enter TAF:")
hours_ahead = st.slider("Hours Ahead", 0, 9, 5)

###############################################################################################################

if st.button("Submit"):
    if metar:
        metar_data = decode_metar(metar)
        formatted_metar_data = format_metar(metar_data)
        cloud_rows = format_cloud_details(metar_data['Cloud Details'])

        st.subheader("Decoded METAR")
        metar_table = [
            ["ICAO", formatted_metar_data["ICAO"]],
            ["Day", formatted_metar_data["Day"]],
            ["Start Time", formatted_metar_data["Start Time"]],
            ["End Time", formatted_metar_data["End Time"]],
            ["Wind Direction", formatted_metar_data["Wind Direction"]],
            ["Wind Speed", formatted_metar_data["Wind Speed"]],
            ["Wind Gust", formatted_metar_data["Wind Gust"]],
            ["Variable", formatted_metar_data["Variable"]],
            ["Visibility", formatted_metar_data["Visibility"]],
        ] + cloud_rows + [
            ["Temperature", formatted_metar_data["Temperature"]],
            ["Dewpoint", formatted_metar_data["Dewpoint"]],
            ["Spread", formatted_metar_data["Spread"]],
            ["QNH", formatted_metar_data["QNH"]],
            ["Trend Duration", formatted_metar_data["Trend Duration"]],
            ["Trend Change", formatted_metar_data["Trend Change"]],
            ["Warnings", formatted_metar_data["Warnings"]],
        ]

        st.table(metar_table)

        if taf:
            taf_data = decode_taf(taf)
            formatted_taf_data = format_taf(taf_data)

            st.subheader("Decoded TAF")
            st.table(list(formatted_taf_data.items()))

        st.subheader("Analysis")
        # Implement additional analysis if needed
    else:
        st.warning("Please enter a METAR.")
