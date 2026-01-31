#!/usr/bin/env python3
"""
Google Maps API Usage Checker
This script helps you monitor your Google Maps API usage and costs.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_api_usage():
    """Check Google Maps API usage and provide cost estimates."""
    
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("❌ No Google Maps API key found in .env file")
        return
    
    print("🔍 Google Maps API Usage Checker")
    print("=" * 50)
    
    # Google Maps API pricing (as of 2024)
    pricing = {
        'Places API (Nearby Search)': 0.032,  # per request
        'Places API (Text Search)': 0.032,    # per request
        'Places API (Place Details)': 0.017,  # per request
        'Geocoding API': 0.005,               # per request
        'Maps JavaScript API': 0.007,         # per load
    }
    
    print("💰 Current Google Maps API Pricing:")
    print("-" * 40)
    for service, cost in pricing.items():
        print(f"{service}: ${cost:.3f} per request")
    
    print("\n📊 Cost Estimation for Your Web Scraper:")
    print("-" * 40)
    
    # Estimate costs based on your scraper's usage
    locations_searched = 50  # Number of cities in your search
    places_per_location = 20  # Average places found per location
    
    total_places_calls = locations_searched
    total_details_calls = locations_searched * places_per_location
    
    places_cost = total_places_calls * pricing['Places API (Nearby Search)']
    details_cost = total_details_calls * pricing['Places API (Place Details)']
    total_estimated_cost = places_cost + details_cost
    
    print(f"Places API calls: {total_places_calls} × ${pricing['Places API (Nearby Search)']:.3f} = ${places_cost:.3f}")
    print(f"Place Details calls: {total_details_calls} × ${pricing['Places API (Place Details)']:.3f} = ${details_cost:.3f}")
    print(f"Total estimated cost per search: ${total_estimated_cost:.3f}")
    
    print("\n⚠️  IMPORTANT COST MONITORING TIPS:")
    print("-" * 40)
    print("1. Set up billing alerts in Google Cloud Console")
    print("2. Monitor your usage daily at: https://console.cloud.google.com/billing")
    print("3. Set a monthly budget limit (e.g., $50)")
    print("4. Enable API key restrictions to prevent unauthorized use")
    print("5. Consider using the free tier (first $200/month)")
    
    print("\n🔧 How to Set Up Billing Alerts:")
    print("-" * 40)
    print("1. Go to Google Cloud Console → Billing")
    print("2. Click 'Budgets & alerts'")
    print("3. Create a new budget")
    print("4. Set alert thresholds (50%, 90%, 100%)")
    print("5. Add your email for notifications")
    
    print("\n🛡️  API Key Security:")
    print("-" * 40)
    print("1. Restrict your API key to specific IP addresses")
    print("2. Limit to specific APIs (Places API only)")
    print("3. Set up referrer restrictions for web usage")
    print("4. Regularly rotate your API keys")

if __name__ == "__main__":
    check_api_usage()
