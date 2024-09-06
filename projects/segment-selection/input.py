code_name = "118" # 122

campaign_name = "Grand Wagoneer" # Redoxon

countries = ["UAE","KSA","QAT","KWT"] # "UAE", "KSA", "QAT"

segments = ["Young Cosmopolitans","Potential Car Buyers","HNWI"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

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