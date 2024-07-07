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
        'Visibility': re.search(r'\b\d{4}\b', metar).group(),
        'Variable Wind': re.search(r'\d{3}V\d{3}', metar).group() if re.search(r'\d{3}V\d{3}', metar) else 'N/A',
        'Clouds': re.findall(r'(FEW|SCT|BKN|OVC)\d{3}', metar),
        'QNH': convert_qnh(re.search(r'\b(A\d{4}|Q\d{4})\b', metar).group()) if re.search(r'\b(A\d{4}|Q\d{4})\b', metar) else 'N/A',
        'Trend': re.search(r'(TEMPO|BECMG|NOSIG)', metar).group() if re.search(r'(TEMPO|BECMG|NOSIG)', metar) else '',
        'Trend Details': re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar).group(2) if re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar) else ''
    }

    cloud_base = 'N/A'
    base_altitude = 'N/A'
    cloud_ceiling = 'N/A'
    ceiling_altitude = 'N/A'

    for cloud in data['Clouds']:
        try:
            altitude = int(cloud[3:]) * 100
            cloud_type = cloud[:3]
            if cloud_type in ['FEW', 'SCT']:
                cloud_base = cloud_type.capitalize()
                base_altitude = f"{altitude}ft"
            if cloud_type in ['BKN', 'OVC']:
                cloud_ceiling = cloud_type.capitalize()
                ceiling_altitude = f"{altitude}ft"
        except ValueError:
            continue

    data['Cloud Base'] = cloud_base
    data['Base Altitude'] = base_altitude
    data['Cloud Ceiling'] = cloud_ceiling
    data['Ceiling Altitude'] = ceiling_altitude

    temp_dew = re.search(r'\d{2}/\d{2}', metar)
    if temp_dew:
        temp_dew_split = temp_dew.group().split('/')
        data['Temperature'] = temp_dew_split[0]
        data['Dewpoint'] = temp_dew_split[1]
        data['Spread'] = str(int(data['Temperature']) - int(data['Dewpoint']))

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
    if data['Trend']:
        time_local_end = time_local_start + datetime.timedelta(hours=2)
    else:
        time_local_end = time_local_start + datetime.timedelta(minutes=30)

    formatted_data = {
        "ICAO": data["ICAO"],
        "Day": data["Day"],
        "Time": f"{time_local_start.strftime('%H:%M')} - {time_local_end.strftime('%H:%M')} LT",
        "Wind": f"{data['Wind'][:3]}° / {data['Wind'][3:5]}kt",
        "Variable": f"{data['Variable Wind'][:3]}° - {data['Variable Wind'][4:]}°" if data['Variable Wind'] != 'N/A' else "N/A",
        "Visibility": f"{data['Visibility']}m",
        "Cloud Base": data['Cloud Base'],
        "Base Altitude": data['Base Altitude'],
        "Cloud Ceiling": data['Cloud Ceiling'],
        "Ceiling Altitude": data['Ceiling Altitude'],
        "Temperature": f"{data['Temperature']}°C",
        "Dewpoint": f"{data['Dewpoint']}°C",
        "Spread": f"{data['Spread']}°C",
        "QNH": f"{data['QNH'][1:]}hPa" if data['QNH'] != 'N/A' else 'N/A',
        "Trend Duration": data['Trend'].capitalize() if data['Trend'] else '',
        "Trend Change": data['Trend Details'] if data['Trend Details'] else ''
    }

    if "G" in data["Wind"]:
        gust_match = re.search(r'G\d{2}', data["Wind"])
        if gust_match:
            gust = gust_match.group()[1:]
            formatted_data["Wind"] += f" / Gusts {gust}kt"

    if "Trend Change" in formatted_data and formatted_data["Trend Change"]:
        trend_wind_match = re.search(r'\d{3}\d{2}(G\d{2})?KT', formatted_data["Trend Change"])
        if trend_wind_match:
            trend_wind = trend_wind_match.group()
            trend_wind_formatted = f"{trend_wind[:3]}° / {trend_wind[3:5]}kt"
            if "G" in trend_wind:
                gust_match = re.search(r'G\d{2}', trend_wind)
                if gust_match:
                    gust = gust_match.group()[1:]
                    trend_wind_formatted += f" - {gust}kt"
            formatted_data["Trend Change"] = trend_wind_formatted

    return formatted_data

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

if st.button("Submit"):
    if metar:
        metar_data = decode_metar(metar)
        formatted_metar_data = format_metar(metar_data)

        st.subheader("Decoded METAR")
        st.table(list(formatted_metar_data.items()))

        if taf:
            taf_data = decode_taf(taf)
            formatted_taf_data = format_taf(taf_data)

            st.subheader("Decoded TAF")
            st.table(list(formatted_taf_data.items()))

        st.subheader("Analysis")
        # Implement additional analysis if needed
    else:
        st.warning("Please enter a METAR.")
