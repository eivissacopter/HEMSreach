import streamlit as st
import datetime
import re

def decode_metar(metar):
    metar = re.sub(r'[\r\n]+', ' ', metar).strip()  # Remove \r and \n characters

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', metar).group(),
        'Day': re.search(r'\d{2}(?=\d{4}Z)', metar).group(),
        'Time': re.search(r'\d{6}Z', metar).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', metar).group(),
        'Visibility': re.search(r'\b\d{4}\b', metar).group(),
        'Variable Wind': re.search(r'\d{3}V\d{3}', metar).group() if re.search(r'\d{3}V\d{3}', metar) else '',
        'Clouds': re.search(r'(FEW|SCT|BKN|OVC)\d{3}', metar).group() if re.search(r'(FEW|SCT|BKN|OVC)\d{3}', metar) else 'CAVOK',
        'QNH': re.search(r'\bQ\d{4}\b', metar).group(),
        'Trend': re.search(r'(TEMPO|BECMG|NOSIG)', metar).group() if re.search(r'(TEMPO|BECMG|NOSIG)', metar) else '',
        'Trend Details': re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar).group(2) if re.search(r'(TEMPO|BECMG|NOSIG)\s+(.*)', metar) else ''
    }

    if 'Clouds' in data and data['Clouds'] != 'CAVOK':
        cloud_base = re.search(r'\d{3}', data['Clouds'])
        if cloud_base:
            data['Ceiling'] = int(cloud_base.group()) * 100
        else:
            data['Ceiling'] = 'N/A'
    else:
        data['Ceiling'] = 'N/A'

    temp_dew = re.search(r'\d{2}/\d{2}', metar)
    if temp_dew:
        temp_dew_split = temp_dew.group().split('/')
        data['Temperature'] = temp_dew_split[0]
        data['Dewpoint'] = temp_dew_split[1]
        data['Spread'] = str(int(data['Temperature']) - int(data['Dewpoint']))

    return data

def format_metar(data):
    time_utc = datetime.datetime.strptime(data['Time'], '%d%H%MZ')
    time_local = time_utc + datetime.timedelta(hours=2)  # Assuming local time is UTC+2
    formatted_data = {
        "ICAO": data["ICAO"],
        "Day": data["Day"],
        "Time": f"{time_local.strftime('%H:%M')} LT",
        "Wind": f"{data['Wind'][:3]}° / {data['Wind'][3:5]}kt",
        "Variable": f"{data['Variable Wind'][:3]}° - {data['Variable Wind'][4:]}°" if data['Variable Wind'] else "N/A",
        "Visibility": f"{data['Visibility']}m",
        "Clouds": data['Clouds'][:3].capitalize(),
        "Ceiling": f"{data['Ceiling']}ft",
        "Temperature": f"{data['Temperature']}°C",
        "Dewpoint": f"{data['Dewpoint']}°C",
        "Spread": f"{data['Spread']}°C",
        "QNH": f"{data['QNH'][1:]}hPa",  # Remove the 'Q' and add 'hPa'
        "Trend Duration": data['Trend'].capitalize(),
        "Trend Wx Change": data['Trend Details']
    }

    if "G" in data["Wind"]:
        gust_match = re.search(r'G\d{2}', data["Wind"])
        if gust_match:
            gust = gust_match.group()[1:]
            formatted_data["Wind"] += f" / Gusts {gust}kt"

    if "Trend Wx Change" in formatted_data and formatted_data["Trend Wx Change"]:
        trend_wind_match = re.search(r'\d{3}\d{2}(G\d{2})?KT', formatted_data["Trend Wx Change"])
        if trend_wind_match:
            trend_wind = trend_wind_match.group()
            trend_wind_formatted = f"{trend_wind[:3]}° / {trend_wind[3:5]}kt"
            if "G" in trend_wind:
                gust_match = re.search(r'G\d{2}', trend_wind)
                if gust_match:
                    gust = gust_match.group()[1:]
                    trend_wind_formatted += f" - {gust}kt"
            formatted_data["Trend Wx Change"] = trend_wind_formatted

    return formatted_data

st.title("METAR/TAF Decoder")

metar = st.text_area("Enter METAR:")
taf = st.text_area("Enter TAF:")
hours_ahead = st.slider("Hours Ahead", 0, 9, 5)

if st.button("Submit"):
    if metar and taf:
        metar_data = decode_metar(metar)
        formatted_metar_data = format_metar(metar_data)

        st.subheader("Decoded METAR")
        st.table(list(formatted_metar_data.items()))

        # Process TAF similarly as METAR if needed
        # ...

        # Assuming a function analyze_weather exists
        # metar_data, taf_data, visibility, cloud_base, warnings = analyze_weather(metar, taf, hours_ahead)
        # ...

        st.subheader("Analysis")
        # if visibility is not None and cloud_base is not None:
        #     st.write(f"Lowest Visibility in next {hours_ahead} hours: {visibility} meters")
        #     st.write(f"Lowest Cloud Base in next {hours_ahead} hours: {cloud_base} feet")
        # st.write("Warnings:")
        # for warning in warnings:
        #     st.write(f"- {warning}")
    else:
        st.warning("Please enter both METAR and TAF.")
