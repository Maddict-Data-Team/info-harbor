code_name = "999" # 122

campaign_name = "AnyName" # Redoxon

countries = ["BHR"] # "UAE", "KSA", "QAT"

segments = ["Car Owners","HNWI","custom_KFC stores","custom_Fine Dining Night Club"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

dict_custom_segments = { 
    "custom_KFC stores":{
        "type":"POI",
        "General_Category":["food"],
        "Category":["QSR","Restaurant"],
        "Subcategory":["Chicken Restaurant"],
        "GM_Subcategory":["Chicken restaurant"],
        "Chain":["KFC"],
        "radius":60
    },
    "custom_Fine Dining Night Club":{
        "type":"POI",
        "General_Category":["food"],
        "Category":["Fine Dining"],
        "Subcategory":["Night Club"],
        "radius":50
    }
}

excluded_segments = [] #  "Male"

controlled_size = 2000
hg_radius = 3000