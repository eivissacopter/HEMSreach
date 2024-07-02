import streamlit as st
import pandas as pd
import requests
import math
import re
from datetime import datetime, timedelta

# Helicopter bases data
helicopter_bases = [
    {"name": "Christoph 1 Munich", "lat": 48.3539, "lon": 11.7861},
    {"name": "Christoph 2 Frankfurt", "lat": 50.0333, "lon": 8.5706},
    {"name": "Christoph 3 Cologne", "lat": 50.8659, "lon": 7.1427},
    {"name": "Christoph 4 Hanover", "lat": 52.4611, "lon": 9.685},
    {"name": "Christoph 5 Ludwigshafen", "lat": 49.4778, "lon": 8.4336},
    {"name": "Christoph 6 Suhl", "lat": 50.6022, "lon": 10.6994},
    {"name": "Christoph 7 Kassel", "lat": 51.2939, "lon": 9.4633},
    {"name": "Christoph 8 Lünen", "lat": 51.6167, "lon": 7.5167},
    {"name": "Christoph 9 Duisburg", "lat": 51.3667, "lon": 6.7500},
    {"name": "Christoph 10 Wittlich", "lat": 49.9917, "lon": 6.8833},
    {"name": "Christoph 11 Villingen-Schwenningen", "lat": 48.0778, "lon": 8.5250},
    {"name": "Christoph 12 Eutin", "lat": 54.1403, "lon": 10.6211},
    {"name": "Christoph 13 Bielefeld", "lat": 51.9667, "lon": 8.5333},
    {"name": "Christoph 14 Traunstein", "lat": 47.8689, "lon": 12.6406},
    {"name": "Christoph 15 Straubing", "lat": 48.9006, "lon": 12.5731},
    {"name": "Christoph 16 Saarbrücken", "lat": 49.2075, "lon": 7.1094},
    {"name": "Christoph 17 Kempten", "lat": 47.7264, "lon": 10.3142},
    {"name": "Christoph 18 Ochsenfurt", "lat": 49.6625, "lon": 10.0522},
    {"name": "Christoph 19 Uelzen", "lat": 52.9622, "lon": 10.5478},
    {"name": "Christoph 20 Bayreuth", "lat": 49.9778, "lon": 11.6203},
    {"name": "Christoph 22 Ulm", "lat": 48.4019, "lon": 9.9875},
    {"name": "Christoph 23 Koblenz", "lat": 50.3625, "lon": 7.5878},
    {"name": "Christoph 24 Güstrow", "lat": 53.7969, "lon": 12.1753},
    {"name": "Christoph 25 Siegen", "lat": 50.8811, "lon": 8.0164},
    {"name": "Christoph 26 Sande", "lat": 53.5208, "lon": 8.0206},
    {"name": "Christoph 28 Fulda", "lat": 50.5625, "lon": 9.6778},
    {"name": "Christoph 29 Hamburg", "lat": 53.5489, "lon": 9.9894},
    {"name": "Christoph 30 Wolfenbüttel", "lat": 52.1592, "lon": 10.5325},
    {"name": "Christoph 31 Berlin", "lat": 52.555, "lon": 13.2875},
    {"name": "Christoph 32 Ingolstadt", "lat": 48.7675, "lon": 11.4331},
    {"name": "Christoph 33 Senftenberg", "lat": 51.5033, "lon": 14.0161},
    {"name": "Christoph 34 Gießen", "lat": 50.5761, "lon": 8.6736},
    {"name": "Christoph 35 Brandenburg", "lat": 52.4097, "lon": 12.5625},
    {"name": "Christoph 36 Magdeburg", "lat": 52.0967, "lon": 11.6272},
    {"name": "Christoph 37 Nordhausen", "lat": 51.5081, "lon": 10.7953},
    {"name": "Christoph 38 Finsterwalde", "lat": 51.6144, "lon": 13.7106},
    {"name": "Christoph 39 Perleberg", "lat": 53.0842, "lon": 11.8561},
    {"name": "Christoph 40 Bayreuth", "lat": 49.975, "lon": 11.6261},
    {"name": "Christoph 41 Ochsenfurt", "lat": 49.6622, "lon": 10.0511},
    {"name": "Christoph 42 Rendsburg", "lat": 54.3144, "lon": 9.6633},
    {"name": "Christoph 43 Suhl", "lat": 50.6028, "lon": 10.6908},
    {"name": "Christoph 44 Göttingen", "lat": 51.5503, "lon": 9.9339},
    {"name": "Christoph 45 Neuburg", "lat": 48.7383, "lon": 11.1728},
    {"name": "Christoph 46 Neustrelitz", "lat": 53.3642, "lon": 13.0744},
    {"name": "Christoph 47 Dinkelsbühl", "lat": 49.0753, "lon": 10.3431},
    {"name": "Christoph 48 Ulm", "lat": 48.3981, "lon": 9.9803},
    {"name": "Christoph 49 Aalen", "lat": 48.8378, "lon": 10.0933},
    {"name": "Christoph 50 Augsburg", "lat": 48.425, "lon": 10.925},
    {"name": "Christoph 51 Iserlohn", "lat": 51.3911, "lon": 7.7108},
    {"name": "Christoph 52 Nürnberg", "lat": 49.4986, "lon": 11.0783},
    {"name": "Christoph 53 Mannheim", "lat": 49.4811, "lon": 8.5367},
    {"name": "Christoph 54 Freiburg", "lat": 48.0206, "lon": 7.8325},
    {"name": "Christoph 55 Reutlingen", "lat": 48.4911, "lon": 9.2064},
    {"name": "Christoph 56 Gießen", "lat": 50.5817, "lon": 8.6778},
    {"name": "Christoph 57 Worms", "lat": 49.6347, "lon": 8.3508},
    {"name": "Christoph 58 Lüneburg", "lat": 53.2506, "lon": 10.4142},
    {"name": "Christoph 59 Weiden", "lat": 49.6747, "lon": 12.1694},
    {"name": "Christoph 60 Berlin", "lat": 52.5619, "lon": 13.2875},
    {"name": "Christoph 61 Leipzig", "lat": 51.4158, "lon": 12.2883},
    {"name": "Christoph 62 Bamberg", "lat": 49.8983, "lon": 10.9047},
    {"name": "Christoph 63 Haren", "lat": 52.7897, "lon": 7.2192},
    {"name": "Christoph 64 Bielefeld", "lat": 51.9667, "lon": 8.5333},
    {"name": "Christoph 65 Greifswald", "lat": 54.0797, "lon": 13.405},
    {"name": "Christoph 66 Augsburg", "lat": 48.425, "lon": 10.925},
    {"name": "Christoph 67 Ansbach", "lat": 49.2808, "lon": 10.5717},
    {'name': 'Christoph 77 Mainz', 'lat': 49.992, 'lon': 8.247}
]

# Airports with IFR approaches data
airports = [
    {"name": "Frankfurt Airport", "icao": "EDDF", "lat": 50.0379, "lon": 8.5622},
    {"name": "Munich Airport", "icao": "EDDM", "lat": 48.3538, "lon": 11.7861},
    {"name": "Berlin Brandenburg Airport", "icao": "EDDB", "lat": 52.3667, "lon": 13.5033},
    {"name": "Hamburg Airport", "icao": "EDDH", "lat": 53.6303, "lon": 9.9883},
    {"name": "Stuttgart Airport", "icao": "EDDS", "lat": 48.6899, "lon": 9.2219},
    {"name": "Cologne Bonn Airport", "icao": "EDDK", "lat": 50.8659, "lon": 7.1427},
    {"name": "Düsseldorf Airport", "icao": "EDDL", "lat": 51.2894, "lon": 6.7667},
    {"name": "Hannover Airport", "icao": "EDDV", "lat": 52.4611, "lon": 9.685},
    {"name": "Leipzig/Halle Airport", "icao": "EDDP", "lat": 51.4325, "lon": 12.2417},
    {"name": "Nuremberg Airport", "icao": "EDDN", "lat": 49.4986, "lon": 11.0783},
    {"name": "Bremen Airport", "icao": "EDDW", "lat": 53.0475, "lon": 8.7867},
    {"name": "Dresden Airport", "icao": "EDDC", "lat": 51.1328, "lon": 13.7672},
    {"name": "Saarbrücken Airport", "icao": "EDDR", "lat": 49.215, "lon": 7.1094},
    {"name": "Karlsruhe/Baden-Baden Airport", "icao": "EDSB", "lat": 48.7793, "lon": 8.0805},
    {"name": "Münster Osnabrück International Airport", "icao": "EDDG", "lat": 52.1346, "lon": 7.6848},
    {"name": "Memmingen Airport", "icao": "EDJA", "lat": 47.9888, "lon": 10.2394},
    {"name": "Friedrichshafen Airport", "icao": "EDNY", "lat": 47.6713, "lon": 9.5115},
    {"name": "Weeze Airport", "icao": "EDLV", "lat": 51.6022, "lon": 6.1422},
    {"name": "Paderborn Lippstadt Airport", "icao": "EDLP", "lat": 51.6141, "lon": 8.6163},
    {"name": "Erfurt–Weimar Airport", "icao": "EDDE", "lat": 50.98, "lon": 10.958},
    {"name": "Kassel Airport", "icao": "EDVK", "lat": 51.4083, "lon": 9.3775},
    {"name": "Würzburg Airport", "icao": "EDFW", "lat": 49.7619, "lon": 9.9672},
    {"name": "Zurich Airport", "icao": "LSZH", "lat": 47.4581, "lon": 8.5481},
    {"name": "Basel/Mulhouse EuroAirport", "icao": "LFSB", "lat": 47.59, "lon": 7.5292},
    {"name": "Strasbourg Airport", "icao": "LFST", "lat": 48.5383, "lon": 7.6283},
    {"name": "Luxembourg Airport", "icao": "ELLX", "lat": 49.6266, "lon": 6.2115},
    {"name": "Brussels Airport", "icao": "EBBR", "lat": 50.9014, "lon": 4.4844},
    {"name": "Amsterdam Airport Schiphol", "icao": "EHAM", "lat": 52.3086, "lon": 4.7639},
    {"name": "Eindhoven Airport", "icao": "EHEH", "lat": 51.4501, "lon": 5.3745},
    {"name": "Maastricht Aachen Airport", "icao": "EHBK", "lat": 50.9117, "lon": 5.7701},
    {"name": "Prague Airport", "icao": "LKPR", "lat": 50.1008, "lon": 14.26},
    {"name": "Vienna International Airport", "icao": "LOWW", "lat": 48.1103, "lon": 16.5697},
    {"name": "Salzburg Airport", "icao": "LOWS", "lat": 47.7933, "lon": 13.0043},
    {"name": "Linz Airport", "icao": "LOWL", "lat": 48.2333, "lon": 14.1881},
    {"name": "Innsbruck Airport", "icao": "LOWI", "lat": 47.2602, "lon": 11.3439},
    {"name": "Graz Airport", "icao": "LOWG", "lat": 46.9911, "lon": 15.4396},
    {"name": "Klagenfurt Airport", "icao": "LOWK", "lat": 46.6425, "lon": 14.3377},
    {"name": "Bratislava Airport", "icao": "LZIB", "lat": 48.1702, "lon": 17.2127},
    {"name": "Budapest Airport", "icao": "LHBP", "lat": 47.4299, "lon": 19.2616},
    {"name": "Ljubljana Airport", "icao": "LJLJ", "lat": 46.2231, "lon": 14.4567},
    {"name": "Zagreb Airport", "icao": "LDZA", "lat": 45.7429, "lon": 16.0688},
    # Military airports
    {"name": "Ramstein Air Base", "icao": "ETAR", "lat": 49.4369, "lon": 7.6003},
    {"name": "Spangdahlem Air Base", "icao": "ETAD", "lat": 49.9727, "lon": 6.6925},
    {"name": "Geilenkirchen Air Base", "icao": "ETNG", "lat": 50.9608, "lon": 6.0424},
    {"name": "Wiesbaden Army Airfield", "icao": "ETOU", "lat": 50.0498, "lon": 8.3254},
    {"name": "Schwäbisch Hall Airfield", "icao": "ETHL", "lat": 49.1181, "lon": 9.7831},
    {"name": "Büchel Air Base", "icao": "ETSB", "lat": 50.1747, "lon": 7.0633},
    {"name": "Kleine Brogel Air Base", "icao": "EBBL", "lat": 51.1681, "lon": 5.4708},
    {"name": "Volkel Air Base", "icao": "EHVK", "lat": 51.6561, "lon": 5.7075},
    {"name": "Nörvenich Air Base", "icao": "ETNN", "lat": 50.8311, "lon": 6.6583},
    {"name": "Jagel Air Base", "icao": "ETNS", "lat": 54.4592, "lon": 9.5167},
    {"name": "Laage Air Base", "icao": "ETNL", "lat": 53.9181, "lon": 12.2789},
    {"name": "Holzdorf Air Base", "icao": "ETSH", "lat": 51.7678, "lon": 13.1672},
    {"name": "Neuburg Air Base", "icao": "ETSN", "lat": 48.7111, "lon": 11.2167},
    {"name": "Jever Air Base", "icao": "ETNJ", "lat": 53.5339, "lon": 7.8883},
    {"name": "Wunstorf Air Base", "icao": "ETNW", "lat": 52.4575, "lon": 9.4278},
    {"name": "Bückeburg Air Base", "icao": "ETHB", "lat": 52.2789, "lon": 9.0839}
]

# Function to calculate distance between two points using the Haversine formula
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Earth radius in kilometers
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 0.539957  # Convert to nautical miles
    return distance

# Function to get airports within a certain radius
def get_airports_within_radius(base_lat, base_lon, radius_nm):
    nearby_airports = [airport for airport in airports if haversine(base_lon, base_lat, airport['lon'], airport['lat']) <= radius_nm]
    return nearby_airports

# Function to fetch METAR and TAF data
def fetch_weather(icao_code):
    metar_url = f'https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao_code}.TXT'
    taf_url = f'https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{icao_code}.TXT'
    
    metar_response = requests.get(metar_url)
    taf_response = requests.get(taf_url)
    
    metar = metar_response.text.split('\n')[1] if metar_response.status_code == 200 and len(metar_response.text.split('\n')) > 1 else "No data"
    taf = taf_response.text if taf_response.status_code == 200 else "No data"
    
    return metar, taf

# Function to parse METAR visibility and cloud base
def parse_metar(metar):
    try:
        visibility_match = re.search(r'\s(\d{4})\s', metar)
        visibility = int(visibility_match.group(1)) if visibility_match else None
        
        cloud_base_match = re.search(r'\s(BKN|FEW|SCT|OVC)(\d{3})\s', metar)
        cloud_base = int(cloud_base_match.group(2)) * 100 if cloud_base_match else None
        
        return visibility, cloud_base
    except Exception as e:
        st.error(f"Error parsing METAR: {e}")
        return None, None

# Function to parse TAF visibility and cloud base
def parse_taf(taf):
    try:
        forecast_blocks = taf.split(" FM")
        forecasts = []
        now = datetime.utcnow()
        
        for block in forecast_blocks[1:]:
            time_match = re.match(r'(\d{2})(\d{2})/(\d{2})(\d{2})', block)
            if time_match:
                start_hour = int(time_match.group(1))
                start_minute = int(time_match.group(2))
                start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                visibility_match = re.search(r'\s(\d{4})\s', block)
                visibility = int(visibility_match.group(1)) if visibility_match else None
                
                cloud_base_match = re.search(r'\s(BKN|FEW|SCT|OVC)(\d{3})\s', block)
                cloud_base = int(cloud_base_match.group(2)) * 100 if cloud_base_match else None
                
                forecasts.append((start_time, visibility, cloud_base))
        
        return forecasts
    except Exception as e:
        st.error(f"Error parsing TAF: {e}")
        return []

# Function to check weather criteria
def check_weather_criteria(metar, taf):
    try:
        visibility_ok, ceiling_ok = True, True
        metar_visibility, metar_ceiling = parse_metar(metar)
        
        if metar_visibility is not None:
            visibility_ok = metar_visibility >= 3000
        
        if metar_ceiling is not None:
            ceiling_ok = metar_ceiling >= 700
        
        forecasts = parse_taf(taf)
        now = datetime.utcnow()
        future_time = now + timedelta(hours=5)
        
        for forecast_time, forecast_visibility, forecast_ceiling in forecasts:
            if forecast_time > future_time:
                break
            if forecast_visibility is not None:
                visibility_ok = visibility_ok and (forecast_visibility >= 3000)
            if forecast_ceiling is not None:
                ceiling_ok = ceiling_ok and (forecast_ceiling >= 700)
        
        return visibility_ok and ceiling_ok
    except Exception as e:
        st.error(f"Error checking weather criteria: {e}")
        return False

# Streamlit app layout
st.title('Aviation Weather Checker')

# Select base
base_names = [base['name'] for base in helicopter_bases]
selected_base_name = st.selectbox('Select Home Base', base_names)
selected_base = next(base for base in helicopter_bases if base['name'] == selected_base_name)

# Get airports within radius
radius_nm = 200
nearby_airports = get_airports_within_radius(selected_base['lat'], selected_base['lon'], radius_nm)

# Display nearby airports and check weather
st.subheader(f'Airports within {radius_nm} NM of {selected_base_name}')
for airport in nearby_airports:
    metar, taf = fetch_weather(airport['icao'])
    weather_ok = check_weather_criteria(metar, taf)
    
    st.markdown(f"### {airport['name']} ({airport['icao']})")
    st.text(f"METAR: {metar}")
    st.text(f"TAF: {taf}")
    
    if weather_ok:
        st.success("IFR OK")
    else:
        st.error("IFR Not OK")
