import math
from geopy.distance import geodesic
from database import airports

# Function to calculate distance and bearing between two points using the Haversine formula
def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Earth radius in kilometers
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c * 0.539957  # Convert to nautical miles

    # Bearing calculation
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360  # Normalize to 0-360 degrees

    return distance, bearing

# Function to calculate ground speed considering wind
def calculate_ground_speed(cruise_speed_kt, wind_speed, wind_direction, flight_direction):
    relative_wind_direction = math.radians(flight_direction - wind_direction)
    wind_component = wind_speed * math.cos(relative_wind_direction)
    ground_speed = cruise_speed_kt - wind_component  # Correct calculation to subtract wind impact for headwind
    return ground_speed

# Function to get reachable airports within a certain radius
def get_reachable_airports(selected_location, wind_data, total_fuel_kg, cruise_altitude_ft, H145D2_PERFORMANCE):
    base_lat = selected_location['lat']
    base_lon = selected_location['lon']
    wind_speed = wind_data['wind_speed']
    wind_direction = wind_data['wind_direction']
    selected_location_elevation_ft = selected_location.get('elevation_ft', 500)  # Default to 500ft if not available

    climb_performance = H145D2_PERFORMANCE['climb']
    cruise_performance = H145D2_PERFORMANCE['cruise']
    descend_performance = H145D2_PERFORMANCE['descend']

    # Calculate climb time using selected location elevation
    climb_time_hours = (cruise_altitude_ft - selected_location_elevation_ft) / climb_performance['climb_rate_fpm'] / 60

    # Calculate fuel burn for climb
    climb_fuel_burn = climb_time_hours * climb_performance['fuel_burn_kgph']

    # Placeholder for remaining trip fuel, to be recalculated based on descent for each airport
    remaining_trip_fuel_kg = total_fuel_kg - climb_fuel_burn

    # Calculate total flight time including climb, cruise, and descent
    descent_time_hours = 0  # Will be recalculated for each airport
    total_flight_time_hours = climb_time_hours + descent_time_hours + (remaining_trip_fuel_kg / cruise_performance['fuel_burn_kgph'])

    reachable_airports = []
    cruise_time_hours = total_flight_time_hours - climb_time_hours - descent_time_hours
    for airport in airports:
        distance, bearing = haversine(base_lon, base_lat, airport['lon'], airport['lat'])
        ground_speed_kt = calculate_ground_speed(cruise_performance['speed_kt'], wind_speed, wind_direction, bearing)
        if ground_speed_kt <= 0:
            continue
        time_to_airport_hours = distance / ground_speed_kt
        if time_to_airport_hours <= cruise_time_hours:
            reachable_airports.append((airport, distance, bearing, ground_speed_kt, time_to_airport_hours))
    reachable_airports.sort(key=lambda x: x[1])
    return reachable_airports
