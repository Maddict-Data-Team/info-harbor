# Input data for POI creation
# Format: list of dictionaries with long, lat, name, country, city, radius (optional)

# Campaign code name (e.g., 122) - this will be used to create table {code_name}_pois
code_name = 173

pois = [
    {
        "longitude": 55.7268202,
        "latitude": 24.2449487,
        "name": "Al Jimi Mall",
        "country": "UAE",
        "city": "Dubai",
        "radius": 325  # Optional: radius in meters (default: 50 if not specified)
    },
    # {
    #     "longitude": 46.6753,
    #     "latitude": 24.7136,
    #     "name": "Riyadh Park",
    #     "country": "KSA",
    #     "city": "Riyadh"
    #     "radius": 325  # Optional: radius in meters (default: 50 if not specified)
    # },

    # Add more POIs here as needed
]

