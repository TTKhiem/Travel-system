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
            params["max_price"] = price_mapping[price_range]["max"]
            
        if rating_range in rating_mapping:
            params["hotel_class"] = rating_mapping[rating_range]
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    def fetch_address_worker(self, hotel):
        try:
            gps = hotel.get("gps_coordinates")
            if gps:
                url = f"https://api.geoapify.com/v1/geocode/reverse?lat={gps['latitude']}&lon={gps['longitude']}&apiKey={self.geo_api_key}"
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data["features"]:
                        hotel["address"] = data["features"][0]["properties"]["formatted"]
                    else:
                        hotel["address"] = "Address not found"
                else:
                    hotel["address"] = "GeoApify Error"
            else:
                hotel["address"] = "No GPS Data"
        except Exception as e:
            hotel["address"] = f"Error: {str(e)}"
        return hotel

    def export_data(self, search_results):
        hotel_list = search_results.get("properties")
        
        if hotel_list:
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            
            print(f"Processing {len(hotel_list)} hotels with multi-threading...")
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=18) as executor:
                future_to_hotel = {executor.submit(self.fetch_address_worker, hotel): hotel for hotel in hotel_list}
                
                for future in as_completed(future_to_hotel):
                    future.result()

            print(f"Address fetching completed in {time.time() - start_time:.2f} seconds.")

            count = 0
            for hotel in hotel_list:
                hotel["id"] = f"{count + 1:02}"
                
                file_path = os.path.join(output_directory, f"{count + 1:02}.json")
                with open(file_path, 'w', encoding='utf-8') as p:
                    json.dump(hotel, p, ensure_ascii=False, indent=4)
                count += 1
            
            with open("full_hotel_lists.json", 'w', encoding='utf-8') as f:
                json.dump(hotel_list, f, ensure_ascii=False, indent=4)
            
            print(f"Successfully exported {count} hotels.")

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