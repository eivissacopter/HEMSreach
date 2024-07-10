def calculate_fuel_policy(total_fuel_kg, cruise_fuel_burn, alternate_required, alternate_fuel):
    system_test_and_air_taxi = 37
    holding_final_reserve = 100
    air_taxi_to_parking = 20
    contingency_fuel = 0.1 * (total_fuel_kg - holding_final_reserve - system_test_and_air_taxi - air_taxi_to_parking)
    trip_fuel_kg = total_fuel_kg - (system_test_and_air_taxi + holding_final_reserve + air_taxi_to_parking + contingency_fuel)

    if not alternate_required:
        fifteen_min_fuel = cruise_fuel_burn * 0.25
        trip_fuel_kg -= fifteen_min_fuel
        approach_fuel = 30
    else:
        fifteen_min_fuel = 0
        approach_fuel = 60

    trip_fuel_kg -= (alternate_fuel + approach_fuel)

    fuel_data = {
        "Fuel Policy": ["System Test / Air Taxi", "Trip Fuel", "Final Reserve", "15 Minutes Fuel" if not alternate_required else "Alternate Fuel", "Approach Fuel", "Air Taxi to Parking", "Contingency Fuel"],
        "Fuel (kg)": [system_test_and_air_taxi, round(trip_fuel_kg), holding_final_reserve, round(fifteen_min_fuel) if not alternate_required else round(alternate_fuel), approach_fuel, air_taxi_to_parking, round(contingency_fuel)]
    }

    return fuel_data, trip_fuel_kg
