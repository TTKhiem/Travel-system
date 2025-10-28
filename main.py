import os
import json
import glob
from flask import Flask, request, jsonify, render_template, redirect, url_for
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

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
        
        serp_api_key = os.getenv("SERPAPI_KEY")
        print(f"Tìm dữ liệu của {city}...")
        search_api = HotelSearchAPI(serp_api_key)
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

@app.route('/hotel/<hotel_id>')
def hotel_detail(hotel_id):
    # Load hotel data from the full hotel list
    try:
        output_directory = "fetched_data"
        if not os.path.exists("full_hotel_lists.json") or not os.path.exists(output_directory):
            return render_template('hotel_detail.html', 
                                 hotel=None, 
                                 error="No hotel data found")
        with open(os.path.join(output_directory, f"{hotel_id}.json"), 'r', encoding= 'utf-8') as p:
            hotel = json.load(p)
        return render_template("hotel_detail.html", hotel=hotel)
            
    except Exception as e:
        print(f"Error loading hotel data: {e}")
        return render_template('hotel_detail.html', 
                             hotel=None, 
                             error="Error loading hotel data")

@app.post('/api/hotel_chat')
def hotel_chat():
    try:
        payload = request.get_json(force=True) or {}
        user_message = (payload.get('message') or '').strip()
        hotel = payload.get('hotel') or {}

        if not user_message:
            return jsonify({"error": "message is required"}), 400

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            return jsonify({"error": "GEMINI_API_KEY is not set in environment"}), 500

        output_directory = "fetched_data"
        with open(os.path.join(output_directory, f"{hotel["id"]}.json"), 'r', encoding='utf-8') as p:
            data = json.load(p)
        json_string = json.dumps(data, indent=2, ensure_ascii=False)
        system_context = {
            f"You are a helpful hotel assistant chatbot. Answer concisely, with practical and visitor-friendly information."
            f"You may search for some information that is not included in the data to answer"
            f"Respond transparently and suggest alternatives. The data is packed in {json_string}"
        }

        prompt = (
            f"Context:\n{system_context}\n\nUser question: {user_message}\n"
        )

        client = genai.Client(api_key= gemini_api_key)
        response = client.models.generate_content (
            model = 'gemini-2.5-flash', contents = prompt
        )
        text = (getattr(response, 'text', None) or '').strip()
        if not text and hasattr(response, 'candidates') and response.candidates:
            try:
                text = response.candidates[0].content.parts[0].text
            except Exception:
                text = ''

        if not text:
            text = "Sorry, I couldn't generate a response right now. Please try again."

        return jsonify({"reply": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)