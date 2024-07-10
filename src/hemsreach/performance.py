# performance.py

H145D2_PERFORMANCE = {
    'climb': {
        'speed_kt': 90,           # Climb speed in knots
        'fuel_burn_kgph': 250,    # Fuel burn during climb in kg per hour
        'climb_rate_fpm': 900    # Climb rate in feet per minute
    },
    'cruise': {
        'speed_kt': 115,          # Cruising speed in knots
        'fuel_burn_kgph': 250     # Fuel burn in kg per hour
    },
    'descend': {
        'speed_kt': 120,          # Descend speed in knots
        'fuel_burn_kgph': 220,    # Fuel burn during descend in kg per hour
        'descend_rate_fpm': 500  # Descend rate in feet per minute
    }
}

#############################################################################

    # Expandable section for performance parameters
    with st.expander("Performance"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            climb_speed = st.number_input("Climb Speed (kt)", value=90)
            cruise_speed = st.number_input("Cruise Speed (kt)", value=110)
            descend_speed = st.number_input("Descend Speed (kt)", value=120)
        
        with col2:
            climb_fuel_burn = st.number_input("Climb Fuel (kg/h)", value=250)
            cruise_fuel_burn = st.number_input("Cruise Fuel (kg/h)", value=250)
            descend_fuel_burn = st.number_input("Descend Fuel (kg/h)", value=220)
        
        with col3:
            climb_rate = st.number_input("Climb Rate (fpm)", value=1000)
            performance_penalty = st.number_input("Speed Penalty (%)", value=0)
            descend_rate = st.number_input("Descend Rate (fpm)", value=500)
