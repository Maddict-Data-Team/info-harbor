code_name = "183" # 122

campaign_name = "Galleria Placelift 26Q1" # Redoxon

countries = ["UAE"] #,"","","",""] # ,
# segments = [
#     "Car Owners",
#     "Potential Car Buyers",
#     "Outdoor Lovers",
#     "Families"
# ]

# ,"Custom_Foodies"
# KSA 
# # z


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
    "custom_Business":{
        "type":"POI",
        "General_Category":["Business"],
        "radius":80
    },      
    # "custom_Fine Dining Night Club":{
    #     "type":"POI",
    #     "General_Category":["food"],
    #     "Category":["Fine Dining"],
    #     "Subcategory":["Night Club"],
    #     "radius":50
    # }
}

segments = list(dict_custom_segments.keys())

excluded_segments = []  #  "Male"

controlled_size = 50000

hg_radius = 3000
