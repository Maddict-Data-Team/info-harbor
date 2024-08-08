code_name = "999" # 122

campaign_name = "AnyName" # Redoxon

countries = ["BHR"] # "UAE", "KSA", "QAT"

segments = ["Car Owners","custom_pizza_stores"]  # "Potential Car Buyers", "University Attendees", "Car Owners", "Male", "Business Professionals"

dict_custom_segments = { 
    "custom_pizza_stores":{
        "type":"POI",
        "General_Category":["food"],
        "Category":["QSR","Restaurant","Fine Dining"],
        "Subcategory":["Chicken Restaurant","Night Club"],
        "GM_Subcategory":["Chicken restaurant","Night Club"],
        "Chain":["KFC"],
        "radius":123
    }
}

excluded_segments = [] #  "Male"

controlled_size = 2000