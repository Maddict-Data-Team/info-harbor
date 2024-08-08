code_name = "999" # 122

campaign_name = "AnyName" # Redoxon

countries = ["BHR","UAE"] # "UAE", "KSA", "QAT"

segments = ["Car Owners","HNWI","Near By Residents","custom_KFC stores","custom_Fine Dining Night Club"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

dict_custom_segments = { 
    "custom_pizza_stores":{
        "type":"POI",
        "General_Category":["food"],
        "Category":["QSR","Restaurant"],
        "Subcategory":["Chicken Restaurant"],
        "GM_Subcategory":["Chicken restaurant"],
        "Chain":["KFC"],
        "radius":123
    },
    "custom_Fine Dining Night Club":{
        "type":"POI",
        "General_Category":["food"],
        "Category":["Fine Dining"],
        "Subcategory":["Night Club"],
        "radius":123
    }
}

excluded_segments = [] #  "Male"

controlled_size = 2000