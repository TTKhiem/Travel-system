import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv
load_dotenv()

output_directory = "fetched_data"

def enlarge_thumbnail(thumbnail_url, width, height):
    if not thumbnail_url:
        return None
    base_url = thumbnail_url.split('=')[0]
    return f"{base_url}=w{width}-h{height}-k-no"

class HotelSearchAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.geo_api_key = os.getenv("GEOAPIFY_KEY")

    def search_hotels(self, location, price_range=None, rating_range=None, amenities=None):
        price_mapping = {
            "0-500000": {"min": 1, "max": 500000},
            "500000-1000000": {"min": 500000, "max": 1000000},
            "1000000-2000000": {"min": 1000000, "max": 2000000},
            "500000-2000000": {"min": 500000, "max": 2000000},
            "2000000+": {"min": 2000000, "max": None}
        }
         
        rating_mapping = {
            "4-5": "4, 5", 
            "3-5": "3, 4, 5",
            "2-3": "2, 3"
        }

        amenities_mapping = {
            "Pet-friendly": "19",
            "Pool": "5",
            "Fitness centre": "7",
            "Bar": "15",
            "Free Wi-Fi": "35",
            "Air-conditioned": "40",
            "Child-friendly": "12"
        }
        
        params = {
            "engine": "google_hotels",
            "q": f"hotels in {location}",
            "check_in_date": date.today(),
            "check_out_date": date.today() + timedelta(days = 1),
            "gl": "vn",  
            "hl": "vi",  
            "currency": "VND",
            "api_key": self.api_key,
        }
        
        if price_range in price_mapping:
            params["min_price"] = price_mapping[price_range]["min"]
            if price_mapping[price_range]["max"]:
                params["max_price"] = price_mapping[price_range]["max"]
            
        if rating_range in rating_mapping:
            params["hotel_class"] = rating_mapping[rating_range]
        
        if amenities:
            # Single amenity is passed only
            if isinstance(amenities, str):
                amenities = [amenities]
            # Map names to IDs
            selected_ids = []
            for a in amenities:
                if a in amenities_mapping:
                    selected_ids.append(amenities_mapping[a])
            if selected_ids:
                params['amenities'] = ",".join(selected_ids)
        try:
            print(f"Fetching hotel list for: {location}...")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            properties = data.get('properties')
            if properties:
                for hotel in properties:
                    images = hotel.get('images', [])
                    for img in images:
                        thumbnail = img['thumbnail']
                        img['original_image'] = enlarge_thumbnail(thumbnail, 1920, 1280)
            return data.get("properties", [])

        except requests.exceptions.RequestException as e:
            print(f"Error searching hotels: {e}")
            return []
        
    def get_hotel_details(self, property_token):
        params = {
            "engine": "google_hotels",
            "q": "hotel detail", # Query giả, quan trọng là property_token
            "check_in_date": date.today(),
            "check_out_date": date.today() + timedelta(days=1),
            "gl": "vn",  
            "hl": "vi",  
            "currency": "VND",
            "property_token": property_token,
            "api_key": self.api_key,
        }
        try:
            print(f"Fetching details for token: {property_token}...")
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data:
                images = data.get('images', [])
                for img in images:
                    thumbnail = img['thumbnail']
                    img['original_image'] = enlarge_thumbnail(thumbnail, 1920, 1280)
                return data
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching detail: {e}")
            return None