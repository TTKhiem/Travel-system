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
from datetime import datetime, timedelta

from hotel_search import HotelSearchAPI
import database

# Load API key lưu trong .env
load_dotenv()

app = Flask(__name__)
app.config['DATABASE'] = database.DATABASE
app.secret_key = os.getenv('APP_SECRET')
database.init_app(app)

@app.context_processor
def inject_user():
    """
    Hàm này chạy trước mỗi template render. 
    Nó tự động lấy thông tin user nếu đã login và gửi xuống template (base.html).
    """
    user_data = None
    if 'user_id' in session:
        db = database.get_db()
        # Lấy thông tin user (username, avatar...) để hiển thị
        user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return dict(user=user_data)

@app.route('/')
def home():
    user_data = None
    if 'user_id' in session:
        db = database.get_db()
        user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('index.html', user = user_data, form_type='login')

@app.route('/register_page')
def register_page():
    return render_template('index.html', form_type='register')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    
    db = database.get_db()
    try:
        hashed_pw = generate_password_hash(password)
        cursor = db.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_pw))
        user_id = cursor.lastrowid
        db.commit()
        flash("✅ Account created successfully! Please log in.")
        return redirect(url_for('home'))
    except sqlite3.IntegrityError:
        flash("❌ Username already exists.")
        return redirect(url_for('register_page'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = database.get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash("❌ Invalid username or password.")
            return render_template('index.html')
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

@app.route('/favorites', methods=['POST'])
def save_favorites():
    # Kiểm tra login bằng user_id
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    token = data.get('property_token')
    preview_info = {
        "name": data.get('name'),
        "image": data.get('image'),
        "price": data.get('price'),
        "address": data.get('address'),
    }
    preview_json = json.dumps(preview_info, ensure_ascii=False)
    user_id = session['user_id'] 
    
    db = database.get_db()
    try:
        db.execute("INSERT OR IGNORE INTO favorite_places (user_id, property_token, preview_data) VALUES (?, ?, ?)", (user_id, token, preview_json))
        db.commit()
        return jsonify({"message": "Saved into Favorites:"}), 200
    except Exception as e:
        print(e)
        return jsonify({"message": "Failed!"}), 500
    
def load_favorites(user_id):
    db = database.get_db()
    # Query trực tiếp bằng user_id
    rows = db.execute("SELECT property_token, preview_data FROM favorite_places WHERE user_id=?", (user_id,)).fetchall()
    favorites = []
    for row in rows:
        data = json.loads(row['preview_data'])
        data['property_token'] = row['property_token']
        favorites.append(data)
    return favorites

@app.route('/my-favorites')
def my_favorites():
    # Kiểm tra login
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    # SỬA: Truyền user_id vào hàm load
    favorites = load_favorites(session['user_id']) 
    return render_template('favorites.html', favorites=favorites)

@app.route('/favorites/remove', methods=['POST'])
def remove_favorite():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    token = data.get('property_token')
    
    # SỬA: Lấy user_id từ session
    user_id = session['user_id']
    
    db = database.get_db()
    db.execute(
        "DELETE FROM favorite_places WHERE user_id = ? AND property_token = ?",
        (user_id, token)
    )
    db.commit()
    return jsonify({"message": "Removed"}), 200

@app.route('/hotel_results', methods=['POST'])
def api_filter():
    # Kiểm tra đăng nhập
    if 'user_id' not in session:
        flash("❌ Vui lòng đăng nhập để sử dụng tính năng tìm kiếm!")
        return redirect(url_for('home'))
    
    city = request.form.get('city')
    if not city:
        flash("Hãy chọn địa điểm")
        return redirect(url_for('home'))
    price_range = request.form.get('price_range')
    rating_range = request.form.get('rating')
    amenities = request.form.get('amenities')

    try:
        serp_api_key = os.getenv("SERPAPI_KEY")
        search_api = HotelSearchAPI(serp_api_key)
        search_results = search_api.search_hotels(city, price_range, rating_range, amenities)
        
        return render_template('hotel_results.html', hotels = search_results,
                               search_params = {
                                   'city:': city,
                                   'price_range': price_range,
                                   'rating_range': rating_range,
                                   'amenity': amenities
                               })
    except Exception as e:
        return render_template('hotel_results.html', 
                            hotels=[], 
                            error=f"Error loading data: {str(e)}")
    
@app.route('/hotel/<property_token>')
def hotel_detail(property_token):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = database.get_db()
    cached_row = db.execute("SELECT data, created_at FROM hotel_cache WHERE token = ?", (property_token,)).fetchone()
    hotel_data = None
    use_cache = False
    # Case 1: Đã cache database khách sạn
    if cached_row:
        # Cache chỉ valid trong 5 ngày
        stored_time = datetime.strptime(cached_row['created_at'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() - stored_time < timedelta(days=5):
            print(f"Cached DB: {property_token}")
            hotel_data = json.loads(cached_row['data'])
            use_cache = True
        else:
            print(f"Cache EXPIRED (> 5 days): {property_token}")

    # Case 2: Chưa có -> Gọi API fetch về và lưu lại
    if not use_cache:
        print(f"Fetching fresh data from API: {property_token}")
        try:
            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)
            hotel_data = search_api.get_hotel_details(property_token)
            
            if hotel_data:
                # Bổ sung property_token vào file json để tiện dùng sau này
                hotel_data['property_token'] = property_token 
                # Lưu file Cache
                json_string = json.dumps(hotel_data, ensure_ascii = False)
                db.execute("INSERT OR REPLACE INTO hotel_cache (token, data) VALUES (?, ?)", (property_token, json_string))
                db.commit()
        except Exception as e:
            print(f"Error fetching details: {e}")
            if cached_row:
                 print("Khong fetch duoc data, quay lai cache cu.")
                 hotel_data = json.loads(cached_row['data'])
            else:
                return render_template('hotel_detail.html', error="Không thể tải dữ liệu khách sạn.")

    if not hotel_data:
        return render_template('hotel_detail.html', error="Không tìm thấy khách sạn.")
    
    dynamic_price = request.args.get('price')
    if dynamic_price:
        # Đảm bảo cấu trúc dict tồn tại để không bị lỗi KeyError
        if 'rate_per_night' not in hotel_data:
            hotel_data['rate_per_night'] = {}
            
        hotel_data['rate_per_night']['lowest'] = dynamic_price
        hotel_data['is_dynamic_price'] = True 

    #  Lưu check-in/out để hiển thị hoặc dùng cho chatbot context
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    if check_in and check_out:
        hotel_data['search_context'] = {'check_in': check_in, 'check_out': check_out}
    
    # --- XỬ LÝ LỌC & SẮP XẾP REVIEW ---
    filter_rating = request.args.get('filter_rating')
    sort_review = request.args.get('sort_review', 'newest') # Mặc định là newest

    # Xây dựng câu truy vấn động
    query = "SELECT * FROM user_reviews WHERE property_token = ?"
    params = [property_token]

    if filter_rating and filter_rating.isdigit():
        query += " AND rating = ?"
        params.append(int(filter_rating))

    if sort_review == 'oldest':
        query += " ORDER BY created_at ASC"
    elif sort_review == 'highest':
        query += " ORDER BY rating DESC, created_at DESC"
    elif sort_review == 'lowest':
        query += " ORDER BY rating ASC, created_at DESC"
    else: # Default newest
        query += " ORDER BY created_at DESC"

    # Thực thi query
    local_reviews = db.execute(query, tuple(params)).fetchall()
    # ----------------------------------

    # Kiểm tra hàm Favorites
    is_favorite = False
    if 'user_id' in session:
        user_id = session['user_id']
        fav_check = db.execute("SELECT 1 FROM favorite_places WHERE user_id=? AND property_token=?", (user_id, property_token)).fetchone()
        if fav_check:
            is_favorite = True
    return render_template("hotel_detail.html", hotel=hotel_data, local_reviews=local_reviews, is_favorite=is_favorite)

@app.route('/hotel/review', methods=['POST'])
def add_review():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    property_token = request.form.get('property_token')
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    username = session['username']
    
    # Lấy lại các tham số URL cũ để redirect về đúng trang thái cũ (giá, ngày)
    price = request.form.get('current_price')
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')

    if property_token and rating:
        db = database.get_db()
        db.execute(
            "INSERT INTO user_reviews (property_token, username, rating, comment) VALUES (?, ?, ?, ?)",
            (property_token, username, int(rating), comment)
        )
        db.commit()
        flash("✅ Cảm ơn bạn đã đánh giá!")
    else:
        flash("❌ Vui lòng chọn số sao.")

    # Redirect lại trang chi tiết
    return redirect(url_for('hotel_detail', 
                            property_token=property_token,
                            price=price,
                            check_in=check_in,
                            check_out=check_out))

@app.post('/api/summarize_reviews')
def summarize_reviews():
    try:
        data = request.get_json(force=True)
        property_token = data.get('property_token')
        
        if not property_token:
            return jsonify({'error': 'Missing token'}), 400

        db = database.get_db()
        # Lấy 20 review gần nhất để tóm tắt (tránh quá dài)
        reviews = db.execute(
            "SELECT rating, comment FROM user_reviews WHERE property_token = ? AND comment IS NOT NULL ORDER BY created_at DESC LIMIT 20", 
            (property_token,)
        ).fetchall()

        if not reviews:
            return jsonify({'summary': None}) # Chưa có đánh giá

        # Ghép các review thành một đoạn văn bản
        reviews_text = "\n".join([f"- {r['rating']} sao: {r['comment']}" for r in reviews if r['comment'].strip()])
        
        if not reviews_text:
             return jsonify({'summary': None})

        # Prompt cho Gemini
        prompt = (
            f"Dưới đây là các đánh giá của khách hàng về một khách sạn:\n"
            f"{reviews_text}\n\n"
            f"Yêu cầu: Hãy viết một đoạn tóm tắt ngắn gọn (khoảng 3-4 câu) bằng tiếng Việt về ưu điểm và nhược điểm chính của khách sạn này dựa trên các đánh giá trên. "
            f"Văn phong khách quan, hữu ích cho người định đặt phòng."
        )

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        return jsonify({'summary': response.text})

    except Exception as e:
        print(f"Summarize Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.post('/api/hotel_chat')
def hotel_chat():
    try:
        payload = request.get_json(force=True) or {}
        user_message = (payload.get('message') or '').strip()
        property_token = payload.get('property_token')
        dynamic_context = payload.get('dynamic_context') or {}
        hotel_fallback = payload.get('hotel_fallback') or {}

        if not user_message:
            return jsonify({"error": "message is required"}), 400

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            return jsonify({"error": "GEMINI_API_KEY is not set in environment"}), 500

        hotel_data = {}
        if property_token:
            db = database.get_db()
            row = db.execute("SELECT data FROM hotel_cache WHERE token = ?", (property_token,)).fetchone()
            
            if row:
                hotel_data = json.loads(row['data'])
            else:
                hotel_data = hotel_fallback
        else:
            hotel_data = hotel_fallback

        # 3. Chuẩn bị Context cho Gemini
        # Trích xuất thông tin động để AI biết
        current_price = dynamic_context.get('price', 'N/A')
        check_in = dynamic_context.get('check_in', 'N/A')
        check_out = dynamic_context.get('check_out', 'N/A')

        # Convert data khách sạn sang string
        hotel_data_str = json.dumps(hotel_data, indent=2, ensure_ascii=False)

        # Prompt kỹ thuật (System Instruction)
        system_instruction = (
            f"You are a helpful and professional AI assistant for a hotel booking platform. "
            f"Your task is to answer visitor questions based STRICTLY on the provided data below.\n\n"
            
            f"--- DYNAMIC CONTEXT (Current User Session) ---\n"
            f"- Current Price being viewed: {current_price} (for dates: {check_in} to {check_out}).\n"
            f"- If the user asks about the price, confirm this value for their selected dates.\n\n"
            
            f"--- HOTEL STATIC INFORMATION ---\n"
            f"{hotel_data_str}\n"
            f"-----------------------------------\n\n"
            
            f"Guidelines:\n"
            f"1. Answer concisely and politely.\n"
            f"2. Use the language that the user is using (e.g., if they ask in Vietnamese, answer in Vietnamese).\n"
            f"3. If the information is not provided in the data, honestly state that you don't have that information. Do not fabricate facts."
        )
        prompt = f"{system_instruction}\n\nUser Question: {user_message}"

        # 4. Gọi Gemini API
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            return jsonify({"error": "Missing GEMINI_API_KEY"}), 500

        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)

        reply_text = response.text if response.text else "Xin lỗi, AI đang bận."

        return jsonify({"reply": reply_text})

    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.post('/api/compare_ai')
def compare_ai_analysis():
    try:
        data = request.get_json()
        hotels = data.get('hotels', []) # Danh sách các khách sạn từ Frontend gửi về
        if len(hotels) < 2:
            return jsonify({'reply': "Cần ít nhất 2 khách sạn để so sánh."})

        prompt_content = "Bạn là một chuyên gia du lịch. Hãy so sánh ngắn gọn các khách sạn sau đây giúp tôi chọn lựa:\n"
        for h in hotels:
            prompt_content += f"- {h['name']}: Giá {h.get('rate_per_night', {}).get('lowest', 'N/A')}, "
            prompt_content += f"Đánh giá {h.get('overall_rating', 'N/A')}/5 ({h.get('reviews', 0)} reviews). "
            amenities = ", ".join(h.get('amenities', [])[:5])
            prompt_content += f"Tiện nghi: {amenities}.\n"

        prompt_content += "\n Hãy một đoạn văn ngắn (khoảng 3-4 câu) bằng tiếng Việt. Chỉ ra điểm mạnh/yếu nổi bật nhất của từng bên và đưa ra lời khuyên nên chọn bên nào tùy theo nhu cầu (ví dụ: gia đình, cặp đôi, tiết kiệm...)."

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_content
        )
        
        return jsonify({'reply': response.text})

    except Exception as e:
        print(f"Compare AI Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    app.run(debug=True)
