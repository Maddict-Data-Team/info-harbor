code_name = "144"  # 122

campaign_name = "Marvel-Thunderbolts"  # Redoxon

countries = ["KSA", "UAE", "KWT"]  # ,"","","",""] # ,

segments = [
    "Young Cosmopolitans",
    "Cinema Goers",
    "Gamers and Activities Frequenters",
    "Fast Food Lovers",
]
# "Gamers and Activities Frequenters","University Attendees","custom_Foodies","Families","Fast Food Lovers",


# "custom_KFC stores","custom_Fine Dining Night Club"
dict_custom_segments = {
    "Custom_QSR Frequenters": {"type": "POI", "Category": ["QSR"], "radius": 50},
    "custom_Foodies": {"type": "POI", "General_Category": ["Food"], "radius": 50},
    "custom_Competitor Car Owners": {
        "type": "POI",
        "General_Category": ["Automotive"],
        "Chain": ["Nissan", "Ford", "Tesla", "Jeep"],
        "radius": 160,
    },
    "custom_Business": {"type": "POI", "General_Category": ["Business"], "radius": 80},
    # "custom_Fine Dining Night Club":{
    #     "type":"POI",
    #     "General_Category":["food"],
    #     "Category":["Fine Dining"],
    #     "Subcategory":["Night Club"],
    #     "radius":50
    # }
}

excluded_segments = []  #  "Male"

controlled_size = 10000

hg_radius = 3000
