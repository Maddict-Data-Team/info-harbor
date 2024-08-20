code_name = "118" # 122

campaign_name = "Grandiose-Q3" # Redoxon

countries = ["UAE"] # "UAE", "KSA", "QAT"

segments = ["custom_Foodies"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

# "custom_KFC stores","custom_Fine Dining Night Club"
dict_custom_segments = { 
    "custom_Foodies":{
        "type":"POI",
        "General_Category":["Food"],
        "Category":["Restaurant", 
        "QSR",
        "Fine Dining",
        "Healthy Restaurant"],
        "radius":80
    }
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