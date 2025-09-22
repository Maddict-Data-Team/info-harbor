#!/usr/bin/env python3
"""
Campaign 145: Out-of-Home Advertising Campaign
Sample OOH campaign configuration
"""
from shared.models.campaign import CampaignConfig, CustomSegment

CAMPAIGN_145_OOH = CampaignConfig(
    code_name="145",
    campaign_name="OOH Billboard Campaign - Highway Network",
    countries=["UAE", "QAT", "KWT"],
    type="OOH",
    
    # Standard segments for OOH analysis
    segments=[
        "Highway Commuters",
        "Business District Visitors", 
        "Airport Travelers",
        "Shopping Center Visitors"
    ],
    
    # Custom segments for OOH locations
    custom_segments={
        "Highway_Billboards": CustomSegment(
            type="POI",
            radius=100,
            Category=["Highway", "Main Road"],
            General_Category=["Transportation", "Infrastructure"],
            Chain=[]
        ),
        "Airport_Displays": CustomSegment(
            type="POI",
            radius=300,
            Category=["Airport", "Terminal"],
            General_Category=["Transportation", "Travel"],
            Chain=["Dubai International", "Hamad International", "Kuwait International"]
        )
    },
    
    # Campaign timing - Active campaign
    start_date="2024-11-15",
    end_date="2025-01-15",
    
    # Configuration parameters
    controlled_size=75000,
    hg_radius=800,
    time_interval=3,  # Every 3 days
    
    # Backend reports for each country
    backend_reports=[2001, 2002, 2003],  # UAE, QAT, KWT
    
    # Excluded segments
    excluded_segments=["Delivery Drivers", "Taxi Drivers"]
) 