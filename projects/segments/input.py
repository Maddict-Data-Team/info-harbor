code_name = "0000" # 122

campaign_name = "Rotana" # Redoxon

countries = ["QAT","KWT","QAT","BHR","OMN"] # ,

segments = ["Business Professionals","Travel Enthusiasts","Hotels and Resorts Frequenters","custom_Muslims"] 
# 

# "custom_KFC stores","custom_Fine Dining Night Club"
dict_custom_segments = { 
    "custom_Muslims":{
        "type":"POI",
        "GM_Subcategory":["Mosque","Religious organization","Religious school"],
        "radius":70
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