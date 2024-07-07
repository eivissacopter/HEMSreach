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

def extract_color_codes(metar):
    color_codes = re.findall(r'\b(BLACKBLU+|BLACK|BLK|BLU|WHT|GRN|YLO|AMB|RED)\b', metar)
    return ' '.join(color_codes)

def extract_cloud_details(metar):
    cloud_details = []
    if 'CAVOK' in metar:
        cloud_details.append(['CAVOK', ''])
    else:
        clouds = re.findall(r'(FEW|SCT|BKN|OVC)(\d{3})', metar)
        for cloud in clouds:
            cloud_type = cloud[0]
            altitude = cloud[1]
            cloud_details.append([cloud_type, altitude])
    return cloud_details

def extract_temp_dew(metar):
    temp_dew = re.search(r'\d{2}/\d{2}', metar)
    if temp_dew:
        temp_dew_split = temp_dew.group().split('/')
        temperature = temp_dew_split[0]
        dewpoint = temp_dew_split[1]
        spread = str(int(temperature) - int(dewpoint))
        return temperature, dewpoint, spread
    return 'N/A', 'N/A', 'N/A'

def detect_warnings(metar):
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
    warnings = []
    for code, description in warnings_patterns.items():
        pattern = r'\b' + re.escape(code) + r'\b'
        if re.search(pattern, metar):
            warnings.append(description)
    return ', '.join(warnings) if warnings else 'N/A'

def decode_metar(metar):
    metar = re.sub(r'[\r\n]+', ' ', metar).strip()  # Remove \r and \n characters
    color_codes_str = extract_color_codes(metar)

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', metar).group(),
        'Day': re.search(r'\d{2}(?=\d{4}Z)', metar).group(),
        'Time': re.search(r'\d{6}Z', metar).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', metar).group() if re.search(r'\d{3}\d{2}(G\d{2})?KT', metar) else 'N/A',
        'Visibility': '9999' if 'CAVOK' in metar else (re.search(r'\b\d{4}\b', metar).group() if re.search(r'\b\d{4}\b', metar) else 'N/A'),
        'Variable Wind': re.search(r'\d{3}V\d{3}', metar).group() if re.search(r'\d{3}V\d{3}', metar) else 'N/A',
        'QNH': convert_qnh(re.search(r'\b(A\d{4}|Q\d{4})\b', metar).group()) if re.search(r'\b(A\d{4}|Q\d{4})\b', metar) else 'N/A',
        'Trend': re.search(r'(TEMPO|BECMG|NOSIG)', metar).group() if re.search(r'(TEMPO|BECMG|NOSIG)', metar) else 'N/A',
        'Trend Details': re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar).group(2) if re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar) else 'N/A',
        'Remarks': re.search(r'RMK (.*)', metar).group(1) if re.search(r'RMK (.*)', metar) else color_codes_str if color_codes_str else 'N/A',
        'Warnings': detect_warnings(metar)
    }

    data['Cloud Details'] = extract_cloud_details(metar)
    data['Temperature'], data['Dewpoint'], data['Spread'] = extract_temp_dew(metar)

    return data

def decode_taf(taf):
    taf = re.sub(r'[\r\n]+', ' ', taf).strip()  # Remove \r and \n characters

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', taf).group(),
        'Day': re.search(r'\d{2}(?=\d{6}Z)', taf).group(),
        'Start Time': re.search(r'\d{6}Z', taf).group(),
        'Validity': re.search(r'\d{4}/\d{4}', taf).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', taf).group(),
        'Visibility': re.search(r'\b\d{4}\b', taf).group(),
        'Clouds': re.findall(r'(FEW|SCT|BKN|OVC)(\d{3})', taf),
        'Changes': re.findall(r'(TEMPO|BECMG|FM|TL|AT|PROB\d{2}) .*?(?= TEMPO|BECMG|FM|TL|AT|PROB\d{2}|$)', taf)
    }

    return data

def format_taf(data):
    time_utc = datetime.datetime.strptime(data['Start Time'], '%d%H%MZ')
    time_local_start = time_utc + datetime.timedelta(hours=2)  # Assuming local time is UTC+2
    validity_start, validity_end = data['Validity'].split('/')
    validity_duration = int(validity_end[:2]) - int(validity_start[:2])

    formatted_data = {
        "ICAO": data["ICAO"],
        "Day": data["Day"],
        "Start Time": time_local_start.strftime('%H%M'),
        "Validity": f"{validity_duration}h",
        "Wind": data["Wind"],
        "Visibility": data["Visibility"],
        "Clouds": ', '.join([cloud[0] + cloud[1] for cloud in data['Clouds']]),
        "Changes": ' | '.join(data['Changes']),
        "Remarks": data['Remarks'],
    }

    return formatted_data

##########################################################################################################

if st.button("Submit", key="submit_button"):
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
            ["Remarks", formatted_metar_data["Remarks"]],
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
