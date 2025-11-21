import os
import json
import glob
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

import database

# Load API key lưu trong .env
load_dotenv()

app = Flask(__name__)
app.config['DATABASE'] = database.DATABASE
app.secret_key = os.getenv('APP_SECRET')
database.init_app(app)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Please fill in all fields.")
            return render_template("register.html")
        db = database.get_db()
        try:
            hashed_pw = generate_password_hash(password)
            cursor = db.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hashed_pw))
            user_id = cursor.lastrowid
            db.commit()
            flash("✅ Account created successfully! Please log in.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("❌ Username already exists.")
            return render_template("register.html")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = database.get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            return redirect(url_for('recommendation'))
        else:
            flash("❌ Invalid username or password.")
            return render_template("login.html")
    return render_template("login.html")

@app.route('/favorites', methods=['POST'])
def save_favorites():
    if "user" not in session:
        return redirect(url_for("login"))
    favorites = request.get_json()
    username = session['user']
    db = database.get_db()
    user = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_id = user['id']
    data_json = json.dumps(favorites)
    db.execute("INSERT INTO favorite_places (user_id, data) VALUES (?, ?)", (user_id, data_json))
    db.commit()
    return jsonify({"message": "Favorites saved successfully!"}), 200

def load_favorites(username):
    db = database.get_db()
    user = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        return []
    user_id = user['id']
    rows = db.execute("SELECT data FROM favorite_places WHERE user_id=?", (user_id,)).fetchall()
    favorites = []
    for row in rows:
        data = json.loads(row['data'])
        favorites.append(data)
    return favorites

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    response = redirect(url_for('home'))

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.set_cookie('session', '', expires=0)
    return response

@app.route('/recommendation')
def recommendation():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('recommendation.html')

@app.route('/filter', methods=['POST'])
def filter_hotels():
    if "user" not in session:
        return redirect(url_for("login"))
    city = request.form['city']
    price_range = request.form['price_range']
    rating_range = str(request.form['rating'])

    try:
        # Su dung SerpAPI trong hotel_search.py de xuat ra cac file JSON
        from hotel_search import HotelSearchAPI
        
        serp_api_key = os.getenv("SERPAPI_KEY")
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
            f"Respond transparently and suggest alternatives. The data is packed in {json_string}. MUST RESPOND IN ENGLISH ONLY"
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
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    app.run(debug=True)