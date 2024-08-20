code_name = "118" # 122

campaign_name = "Grandiose-Q3" # Redoxon

countries = ["UAE"] # "UAE", "KSA", "QAT"

segments = ["custom_Competitors"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

# "custom_KFC stores","custom_Fine Dining Night Club"
dict_custom_segments = { 
    "custom_Competitors":{
        "type":"POI",
        "Chain":["Lulu", "LuLu Market", "Lulu Market", "LuLu Hypermarket", "Carrefour", "Union Coop"],
        "radius":150
    },
    # "custom_Fine Dining Night Club":{
    #     "type":"POI",
    #     "General_Category":["food"],
    #     "Category":["Fine Dining"],
    #     "Subcategory":["Night Club"],
    #     "radius":50
    # }
}

excluded_segments = [] #  "Male"

controlled_size = 2000
# hg_radius = 3000