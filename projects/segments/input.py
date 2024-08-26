code_name = "9999" # 122

campaign_name = "Magnite massive media" # Redoxon

countries = ["EGY"] # "UAE", "KSA", "QAT"

segments = ["custom_Business"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

# "custom_KFC stores","custom_Fine Dining Night Club"
dict_custom_segments = { 
    "custom_Business":{
        "type":"POI",
        "General_Category":["Business"],
        "radius":60
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
hg_radius = 3000