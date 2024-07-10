import streamlit as st
import datetime
import re

###########################################################################################

AVWX_API_KEY = '6za8qC9A_ccwpCc_lus3atiuA7f3c4mwQKMGzW1RVvY'

data_server = st.secrets["data_server"]

###########################################################################################

# Function to fetch METAR and TAF data from AVWX
def fetch_metar_taf_data_avwx(icao, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    metar_url = f"https://avwx.rest/api/metar/{icao}?options=summary"
    taf_url = f"https://avwx.rest/api/taf/{icao}?options=summary"

    try:
        response_metar = requests.get(metar_url, headers=headers)
        response_metar.raise_for_status()
        metar_data = response_metar.json()
    except requests.exceptions.RequestException as e:
        metar_data = f"Error fetching METAR data: {e}"

    try:
        response_taf = requests.get(taf_url, headers=headers)
        response_taf.raise_for_status()
        taf_data = response_taf.json()
    except requests.exceptions.RequestException as e:
        taf_data = f"Error fetching TAF data: {e}"

    return metar_data, taf_data

###########################################################################################

# Function to fetch METAR and TAF data from DWD server with AVWX fallback
def fetch_metar_taf_data(icao, api_key):
    metar_base_url = f"https://{data_server['server']}/aviation/OPMET/METAR/DE"
    taf_base_url = f"https://{data_server['server']}/aviation/OPMET/TAF/DE"

    metar_file_content = find_latest_file(metar_base_url, icao)
    taf_file_content = find_latest_file(taf_base_url, icao)

    metar_data = parse_metar_data(metar_file_content) if metar_file_content else None
    taf_data = parse_taf_data(taf_file_content) if taf_file_content else None

    if not metar_data or not taf_data:
        avwx_metar, avwx_taf = fetch_metar_taf_data_avwx(icao, api_key)
        if not metar_data and isinstance(avwx_metar, dict):
            metar_data = avwx_metar.get('raw', 'No METAR data available')
        if not taf_data and isinstance(avwx_taf, dict):
            taf_data = avwx_taf.get('raw', 'No TAF data available')

    return metar_data, taf_data

# Function to fetch directory listing
def fetch_directory_listing(base_url):
    try:
        response = requests.get(base_url, auth=(data_server["user"], data_server["password"]))
        if response.status_code == 200:
            return response.text
        else:
            st.warning(f"Failed to fetch directory listing from URL: {base_url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching directory listing from URL: {base_url} - Error: {e}")
        return None

# Function to fetch file content via HTTPS
def fetch_file_content(url):
    try:
        response = requests.get(url, auth=(data_server["user"], data_server["password"]))
        if response.status_code == 200:
            return response.content
        else:
            st.warning(f"Failed to fetch data from URL: {url} - Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching data from URL: {url} - Error: {e}")
        return None

# Function to parse the METAR data content
def parse_metar_data(file_content):
    try:
        content = file_content.decode('utf-8').strip()
        metar_message = content.split('METAR')[1].split('=')[0].strip()
        return metar_message
    except Exception as e:
        st.error(f"Error parsing METAR data: {e}")
        return None

# Function to parse the TAF data content
def parse_taf_data(file_content):
    try:
        content = file_content.decode('utf-8').strip()
        taf_message = content.split('TAF')[1].split('=')[0].strip()
        return taf_message
    except Exception as e:
        st.error(f"Error parsing TAF data: {e}")
        return None

# Function to find the latest available file by scanning the directory
def find_latest_file(base_url, airport_code):
    directory_listing = fetch_directory_listing(base_url)
    if directory_listing:
        soup = BeautifulSoup(directory_listing, 'html.parser')
        files = [a['href'] for a in soup.find_all('a', href=True) if f"_{airport_code}_" in a['href']]
        if files:
            latest_file = sorted(files, reverse=True)[0]
            url = f"{base_url}/{latest_file}"
            file_content = fetch_file_content(url)
            return file_content
    return None




###########################################################################################

def convert_qnh(qnh):
    """Convert QNH from inches of mercury (A) to hectopascals (Q)."""
    if qnh.startswith('A'):
        inches = int(qnh[1:]) / 100
        hpa = round(inches * 33.8639)
        return f"Q{hpa}"
    return qnh

def decode_metar(metar):
    metar = re.sub(r'[\r\n]+', ' ', metar).strip()  # Remove \r and \n characters

    # Extract military color codes before parsing the rest
    color_codes = re.findall(r'\b(BLACKBLU+|BLACK|BLK|BLU|WHT|GRN|YLO|AMB|RED)\b', metar)
    color_codes_str = ' '.join(color_codes)
    
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
        'Warnings': []
    }

    cloud_details = []
    if 'CAVOK' in metar:
        cloud_details.append(['CAVOK', ''])
    else:
        clouds = re.findall(r'(FEW|SCT|BKN|OVC)(\d{3})', metar)
        for cloud in clouds:
            cloud_type = cloud[0]
            altitude = cloud[1]
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
        pattern = r'\b' + re.escape(code) + r'\b'
        if re.search(pattern, metar):
            data['Warnings'].append(description)
    
    data['Warnings'] = ', '.join(data['Warnings']) if data['Warnings'] else 'N/A'

    return data

def format_metar(data):
    time_utc = datetime.datetime.strptime(data['Time'], '%d%H%MZ')
    time_local_start = time_utc + datetime.timedelta(hours=2)  # Assuming local time is UTC+2
    if data['Trend'] != 'N/A':
        time_local_end = time_local_start + datetime.timedelta(hours=2)
    else:
        time_local_end = time_local_start + datetime.timedelta(minutes=30)

    formatted_data = {
        "ICAO": data["ICAO"],
        "Day": data["Day"],
        "Start Time": time_local_start.strftime('%H%M'),
        "End Time": time_local_end.strftime('%H%M'),
        "Wind Direction": data["Wind"][:3],
        "Wind Speed": data["Wind"][3:5],
        "Wind Gust": data["Wind"][7:9] if 'G' in data["Wind"] else 'N/A',
        "Variable": f"{data['Variable Wind'][:3]} - {data['Variable Wind'][4:]}" if data['Variable Wind'] != 'N/A' else "N/A",
        "Visibility": data['Visibility'],
        "Temperature": data['Temperature'],
        "Dewpoint": data['Dewpoint'],
        "Spread": data['Spread'],
        "QNH": data['QNH'][1:] if data['QNH'] != 'N/A' else 'N/A',
        "Trend Duration": data['Trend'] if data['Trend'] != 'N/A' else 'N/A',
        "Trend Change": data['Trend Details'] if data['Trend Details'] != 'N/A' else 'N/A',
        "Remarks": data['Remarks'],
        "Warnings": data['Warnings']
    }

    return formatted_data

def format_cloud_details(cloud_details):
    cloud_rows = []
    for i, detail in enumerate(cloud_details):
        cloud_rows.append([f"Cloud {i+1} Type", detail[0]])
        cloud_rows.append([f"Cloud {i+1} Altitude", detail[1]])
    return cloud_rows

#################################################################################################

def decode_taf(taf):
    taf = re.sub(r'[\r\n]+', ' ', taf).strip()  # Remove \r and \n characters

    data = {
        'ICAO': re.search(r'\b[A-Z]{4}\b', taf).group(),
        'Time': re.search(r'\d{6}Z', taf).group(),
        'Validity': re.search(r'\d{4}/\d{4}', taf).group(),
        'Wind': re.search(r'\d{3}\d{2}(G\d{2})?KT', taf).group(),
        'Visibility': re.search(r'\b\d{4}\b', taf).group() if re.search(r'\b\d{4}\b', taf) else 'N/A',
        'Clouds': re.findall(r'(FEW|SCT|BKN|OVC)(\d{3})', taf),
        'Changes': re.findall(r'(TEMPO|BECMG|FM|TL|AT|PROB\d{2}) .*?(?= TEMPO|BECMG|FM|TL|AT|PROB\d{2}|$)', taf)
    }

    return data

def format_taf(data):
    time_utc = datetime.datetime.strptime(data['Time'], '%d%H%MZ')
    time_local_start = time_utc + datetime.timedelta(hours=2)  # Assuming local time is UTC+2
    validity_start, validity_end = data['Validity'].split('/')
    validity_duration = int(validity_end[:2]) - int(validity_start[:2])
    validity_end_time = time_local_start + datetime.timedelta(hours=validity_duration)

    formatted_data = {
        "ICAO": data["ICAO"],
        "Day": time_local_start.strftime('%d'),
        "Start Time": time_local_start.strftime('%H%M'),
        "End Time": validity_end_time.strftime('%H%M'),
        "Wind": data["Wind"],
        "Visibility": data["Visibility"],
        "Clouds": ', '.join([cloud[0] + cloud[1] for cloud in data['Clouds']]) if data['Clouds'] else "CAVOK",
        "Changes": ' | '.join(data['Changes']) if data['Changes'] else ''
    }

    return formatted_data

st.title("METAR/TAF Decoder")

metar = st.text_area("Enter METAR:")
taf = st.text_area("Enter TAF:")

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
        taf_table = [
            ["ICAO", formatted_taf_data["ICAO"]],
            ["Day", formatted_taf_data["Day"]],
            ["Start Time", formatted_taf_data["Start Time"]],
            ["End Time", formatted_taf_data["End Time"]],
            ["Wind", formatted_taf_data["Wind"]],
            ["Visibility", formatted_taf_data["Visibility"]],
            ["Clouds", formatted_taf_data["Clouds"]],
            ["Changes", formatted_taf_data["Changes"]],
        ]

        st.table(taf_table)

    st.subheader("Analysis")
    # Implement additional analysis if needed
else:
    st.warning("Please enter a METAR or TAF.")
