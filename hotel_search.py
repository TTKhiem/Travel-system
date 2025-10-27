# Tim khach san va xuat ket qua ra file json
# Moi lenh args cua SerpAPI tham khao tren: https://serpapi.com/google-hotels-api
import requests
import json
import os
from datetime import date, timedelta
import time
from dotenv import load_dotenv

# Load API key lưu trong .env
load_dotenv()

output_directory = "fetched_data"

class HotelSearchAPI: # Tao class ti import vao file main.py
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
    #
    def search_hotels(self, location, price_range, rating_range):
        # Map de convert theo range filter dat san thanh parameters cua SerpAPI
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
            "check_in_date": date.today(), # Ngày check in là ngày hôm nay
            "check_out_date": date.today() + timedelta(days = 1), # Mặc định check out là ngày hiện tại + 1
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
        
    def export_data(self, search_results):
        api = "aa54f565c7f84e9b87ba9c1f48a3b08f"
        hotel_list = search_results.get("properties") # lay du lieu khach san
        if hotel_list:
            # Tao folder luu du lieu tung khach san
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            
            # Luu du lieu cua tung khach san vao tung file json
            count = 0
            for hotel in hotel_list:
                # Xuất địa chỉ theo tọa đọ dùng GeoAPIFY (Hạn chế requests phải dùng cho SerpAPI)
                # Tìm hiểu JSON format và cách dùng trong: https://apidocs.geoapify.com/playground/geocoding/?searchType=latlon&query=16.049943000000003,%20108.2453194#reverse
                geo_api = os.getenv("GEOAPIFY_KEY")
                gps = hotel.get("gps_coordinates")
                res = requests.get(f"https://api.geoapify.com/v1/geocode/reverse?lat={gps['latitude']}&lon={gps['longitude']}&apiKey={geo_api}")
                hotel["address"] = res.json()["features"][0]["properties"]["formatted"]

                with open(os.path.join(output_directory, f"{count + 1}.json"), 'w', encoding= 'utf-8') as p:
                    json.dump(hotel, p, ensure_ascii= False, indent = 4)
                count += 1 # Counter de track
            
            # Luu du lieu toan bo khach san vao 1 file tong
            with open("full_hotel_lists.json", 'w', encoding= 'utf-8') as f:
                json.dump(hotel_list, f, ensure_ascii = False, indent = 4)
            print(f"Da xuat {count} khach san vao file tong")
        

# Chạy lẻ file hotel_search.py để test tính năng xuất
# Mọi algorithms đều nằm ở class phía trên
def main():
    api_key = "" #fill API_key của ae vào để test
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
