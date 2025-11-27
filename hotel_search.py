import requests
import json
import os
from datetime import date, timedelta
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

output_directory = "fetched_data"

class HotelSearchAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.geo_api_key = os.getenv("GEOAPIFY_KEY")

    def search_hotels(self, location, price_range, rating_range):
        price_mapping = {
            "0-500000": {"min": 0, "max": 500000},
            "500000-1000000": {"min": 500000, "max": 1000000},
            "1000000-2000000": {"min": 1000000, "max": 2000000},
            "2000000+": {"min": 2000000, "max": None}
        }
         
        rating_mapping = {
            "4-5": "4, 5", 
            "3-5": "3, 4, 5",
            "2-3": "2, 3"
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
        
        try:
            print(f"Fetching hotel list for: {location}...")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
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
            return response.json() 
        except requests.exceptions.RequestException as e:
            print(f"Error fetching detail: {e}")
            return None


def main():
    api_key = os.getenv("SERPAPI_KEY")
    search_api = HotelSearchAPI(api_key)
    location = "Hà Nội"
    price_range = "500000-1000000"
    rating_range = "4-5"
    
    print(f"Searching for hotels in {location}...")
    search_results = search_api.search_hotels(location, price_range, rating_range)
    
    if search_results:
        search_api.export_data(search_results)
    else:
        print("Failed to fetch hotel data")

if __name__ == "__main__":
    main()