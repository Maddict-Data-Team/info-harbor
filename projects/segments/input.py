code_name = "145" # 122

campaign_name = "BYD" # Redoxon

countries = ["UAE"]#,"","","",""] # ,

segments = ["Beauty Enthusiasts/Personal Care "]
# ,"Custom_Foodies"
# KSA 
# # z

# KSA 

# "custom_KFC stores","custom_Fine Dining Night Club"
dict_custom_segments = { 
    "Custom_QSR Frequenters":{
        "type":"POI",
        "Category":["QSR"],
        "radius":50
    },
    "custom_Foodies":{
        "type":"POI",
        "General_Category":["Food"],
        "radius":50
    },
        "custom_Competitor Car Owners":{
        "type":"POI",
        "General_Category":["Automotive"],
        "Chain":["Nissan","Ford","Tesla","Jeep"],
        "radius":160
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

excluded_segments = [] #  "Male"

controlled_size = 50000

hg_radius = 3000