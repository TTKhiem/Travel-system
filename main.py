import os
import json
import glob
from flask import Flask, request, jsonify, render_template, redirect, url_for
import pandas as pd
from dotenv import load_dotenv

# Load API key lưu trong .env
load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommendation')
def recommendation():
    return render_template('recommendation.html')

@app.route('/filter', methods=['POST'])
def filter_hotels():
    city = request.form['city']
    price_range = request.form['price_range']
    rating_range = str(request.form['rating'])

    try:
        # Su dung SerpAPI trong hotel_search.py de xuat ra cac file JSON
        from hotel_search import HotelSearchAPI
        
        api_key = os.getenv("SERPAPI_KEY")
        print(f"Tìm dữ liệu của {city}...")
        search_api = HotelSearchAPI(api_key)
        search_results = search_api.search_hotels(city, price_range, rating_range)
        
        # Tạo file khi có khách sạn
        # Khỏi tạo nếu không tìm: 
        # Case: Có data thì load còn ko luôn thì nah :skull:
        if search_results:
            search_api.export_data(search_results)
            with open("full_hotel_lists.json", 'r', encoding='utf-8') as f:
                hotels_data = json.load(f)
        else:
            if os.path.exists("full_hotel_lists.json"):
                with open("full_hotel_lists.json", 'r', encoding='utf-8') as f:
                    hotels_data = json.load(f)
            else:
                hotels_data = []
        
        return render_template('hotel_results.html', 
                            hotels=hotels_data, 
                            search_params={
                                'city': city,
                                'price_range': price_range,
                                'rating_range': rating_range
                            })
    except Exception as e:
        return render_template('hotel_results.html', 
                            hotels=[], 
                            error=f"Error loading data: {str(e)}")

# Phần này là cho trang cụ thể của từng khách sạn ( chưa dev - need fix)
#Uncomment hoặc thay cái khác

# @app.route('/hotel/<int:hotel_id>')
# def hotel_detail(hotel_id):
#     # Load hotel data from the full hotel list
#     try:
#         if not os.path.exists("full_hotel_lists.json"):
#             return render_template('hotel_detail.html', 
#                                  hotel=None, 
#                                  error="No hotel data found")
        
#         # with open("full_hotel_lists.json", 'r', encoding='utf-8') as f:
#             hotels_data = json.load(f)
        
#         if 0 < hotel_id <= 50:
#             with open("full_hotel_lists.json", 'r', encoding='utf-8') as f:
#                 hotels_data = json.load(f)
#             hotel = hotels_data
#             return render_template('hotel_detail.html', hotel=hotel)
#         else:
#             return render_template('hotel_detail.html', 
#                                  hotel=None, 
#                                  error="Hotel not found")
            
#     except Exception as e:
#         print(f"Error loading hotel data: {e}")
#         return render_template('hotel_detail.html', 
#                              hotel=None, 
#                              error="Error loading hotel data")
    


# for debugging - check if data can be fetched from API
# hope dont have to use this bruh
# can be abandoned if wanted
# ------------------------------------ DEBUG ----------------------------------------------------
@app.route('/api/hotels')
def api_hotels():
    """API endpoint to get all hotels from the full hotel list"""
    try:
        if not os.path.exists("full_hotel_lists.json"):
            return jsonify({"error": "No hotel data found"}), 404
        
        with open("full_hotel_lists.json", 'r', encoding='utf-8') as f:
            hotels_data = json.load(f)
        
        return jsonify(hotels_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search')
def search_hotels():
    """Route to trigger hotel search and data extraction"""
    try:
        from hotel_search import HotelSearchAPI
        
        # Use the hardcoded API key
        api_key = "14277ad46ce3a2bd8a75de26cbfc71c4a17e66743a76430f715143cfc6801d0d"
        search_api = HotelSearchAPI(api_key)
        
        # Example search parameters
        location = "Hà Nội"
        price_range = "500000-1000000"
        rating_range = "4-5"
        
        search_results = search_api.search_hotels(location, price_range, rating_range)
        
        if search_results:
            search_api.export_data(search_results)
            return jsonify({
                "success": True,
                "message": "Hotel search completed and data exported"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to fetch hotel data"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })
# ============================================= HET DEBUG ========================================================


if __name__ == '__main__':
    app.run(debug=True)