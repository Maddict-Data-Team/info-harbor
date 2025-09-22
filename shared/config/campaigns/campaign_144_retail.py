#!/usr/bin/env python3
"""
Campaign 144: Retail Intelligence Dashboard
Sample retail campaign configuration
"""
from shared.models.campaign import CampaignConfig, CustomSegment

CAMPAIGN_144_RETAIL = CampaignConfig(
    code_name="144",
    campaign_name="Retail Intelligence - Mall Analysis",
    countries=["KSA", "UAE"],
    type="Retail Intelligence Dashboard",
    
    # Standard segments for retail analysis
    segments=[
        "Shopping Mall Frequenters",
        "Luxury Shoppers",
        "Family Shoppers",
        "Weekend Shoppers"
    ],
    
    # Custom segments for specific retail locations
    custom_segments={
        "Premium_Malls": CustomSegment(
            type="POI",
            radius=500,
            Category=["Shopping Mall", "Department Store"],
            General_Category=["Retail", "Shopping"],
            Chain=["Mall of Emirates", "Dubai Mall", "Riyadh Gallery"]
        ),
        "Electronics_Stores": CustomSegment(
            type="POI", 
            radius=200,
            Category=["Electronics Store", "Mobile Phone Store"],
            General_Category=["Electronics", "Technology"],
            Chain=["Extra", "Jarir", "Sharaf DG"]
        )
    },
    
    # Campaign timing
    start_date="2024-12-01",
    end_date="2024-12-31",
    
    # Configuration parameters
    controlled_size=50000,
    hg_radius=1000,
    time_interval=7,  # Weekly reporting
    
    # Backend reports for each country
    backend_reports=[1001, 1002],  # KSA, UAE
    
    # Excluded segments
    excluded_segments=["Competitor Employees", "Mall Staff"]
) 