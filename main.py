import os
import json
import glob
import re  
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
        user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return dict(user=user_data)

@app.route('/')
def home():
    user_data = None
    if 'user_id' in session:
        db = database.get_db()
        user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('index.html', user=user_data, form_type='login')

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

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = database.get_db()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        try:
            db.execute("""
                UPDATE users 
                SET full_name = ?, email = ?, phone = ?, address = ?
                WHERE id = ?
            """, (full_name, email, phone, address, session['user_id']))
            db.commit()
            flash("✅ Cập nhật hồ sơ thành công!")
        except Exception as e:
            print(e)
            flash("❌ Có lỗi xảy ra, vui lòng thử lại.")
            
        return redirect(url_for('profile'))
    
    user_info = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('profile.html', user_info=user_info)

@app.route('/favorites', methods=['POST'])
def save_favorites():
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
    rows = db.execute("SELECT property_token, preview_data FROM favorite_places WHERE user_id=?", (user_id,)).fetchall()
    favorites = []
    for row in rows:
        data = json.loads(row['preview_data'])
        data['property_token'] = row['property_token']
        favorites.append(data)
    return favorites

@app.route('/my-favorites')
def my_favorites():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    favorites = load_favorites(session['user_id']) 
    return render_template('favorites.html', favorites=favorites)

@app.route('/favorites/remove', methods=['POST'])
def remove_favorite():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    token = data.get('property_token')
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
        
        return render_template('hotel_results.html', hotels=search_results,
                               search_params={
                                   'city:': city,
                                   'price_range': price_range,
                                   'rating_range': rating_range,
                                   'amenity': amenities
                               })
    except Exception as e:
        return render_template('hotel_results.html', hotels=[], error=f"Error loading data: {str(e)}")
    
@app.route('/hotel/<property_token>')
def hotel_detail(property_token):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = database.get_db()
    cached_row = db.execute("SELECT data, created_at FROM hotel_cache WHERE token = ?", (property_token,)).fetchone()
    hotel_data = None
    use_cache = False
    
    if cached_row:
        stored_time = datetime.strptime(cached_row['created_at'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() - stored_time < timedelta(days=5):
            print(f"Cached DB: {property_token}")
            hotel_data = json.loads(cached_row['data'])
            use_cache = True

    if not use_cache:
        print(f"Fetching fresh data from API: {property_token}")
        try:
            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)
            hotel_data = search_api.get_hotel_details(property_token)
            
            if hotel_data:
                hotel_data['property_token'] = property_token 
                json_string = json.dumps(hotel_data, ensure_ascii=False)
                db.execute("INSERT OR REPLACE INTO hotel_cache (token, data) VALUES (?, ?)", (property_token, json_string))
                db.commit()
        except Exception as e:
            print(f"Error fetching details: {e}")
            if cached_row:
                 hotel_data = json.loads(cached_row['data'])
            else:
                return render_template('hotel_detail.html', error="Không thể tải dữ liệu khách sạn.")
    
    if hotel_data:
        try:
            preview_info = {
                "name": hotel_data.get('name'),
                "image": hotel_data.get('images')[0].get('original_image') if hotel_data.get('images') else '',
                "price": hotel_data.get('rate_per_night', {}).get('lowest', 'Liên hệ'),
                "address": hotel_data.get('address')
            }
            preview_json = json.dumps(preview_info, ensure_ascii=False)
            db.execute(
                "INSERT OR REPLACE INTO recently_viewed (user_id, property_token, preview_data, visited_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (session['user_id'], property_token, preview_json)
            )
            db.commit()
        except Exception as e:
            print(f"Lỗi lưu lịch sử: {e}")

    if not hotel_data:
        return render_template('hotel_detail.html', error="Không tìm thấy khách sạn.")
    
    dynamic_price = request.args.get('price')
    if dynamic_price:
        if 'rate_per_night' not in hotel_data:
            hotel_data['rate_per_night'] = {}
        hotel_data['rate_per_night']['lowest'] = dynamic_price
        hotel_data['is_dynamic_price'] = True 

    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    if check_in and check_out:
        hotel_data['search_context'] = {'check_in': check_in, 'check_out': check_out}
    
    filter_rating = request.args.get('filter_rating')
    sort_review = request.args.get('sort_review', 'newest')

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
    else:
        query += " ORDER BY created_at DESC"

    local_reviews = db.execute(query, tuple(params)).fetchall()

    is_favorite = False
    if 'user_id' in session:
        fav_check = db.execute("SELECT 1 FROM favorite_places WHERE user_id=? AND property_token=?", (session['user_id'], property_token)).fetchone()
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

    return redirect(url_for('hotel_detail', property_token=property_token, price=price, check_in=check_in, check_out=check_out))

@app.post('/api/summarize_reviews')
def summarize_reviews():
    try:
        data = request.get_json(force=True)
        property_token = data.get('property_token')
        if not property_token:
            return jsonify({'error': 'Missing token'}), 400

        db = database.get_db()
        reviews = db.execute(
            "SELECT rating, comment FROM user_reviews WHERE property_token = ? AND comment IS NOT NULL ORDER BY created_at DESC LIMIT 20", 
            (property_token,)
        ).fetchall()

        if not reviews:
            return jsonify({'summary': None})

        reviews_text = "\n".join([f"- {r['rating']} sao: {r['comment']}" for r in reviews if r['comment'].strip()])
        
        if not reviews_text:
             return jsonify({'summary': None})

        prompt = (
            f"Dưới đây là các đánh giá của khách hàng về một khách sạn:\n"
            f"{reviews_text}\n\n"
            f"Yêu cầu: Hãy viết một đoạn tóm tắt ngắn gọn (khoảng 3-4 câu) bằng tiếng Việt về ưu điểm và nhược điểm chính của khách sạn này dựa trên các đánh giá trên."
        )

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return jsonify({'summary': response.text})

    except Exception as e:
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
        client = genai.Client(api_key=gemini_api_key)

        hotel_data = {}
        if property_token:
            db = database.get_db()
            row = db.execute("SELECT data FROM hotel_cache WHERE token = ?", (property_token,)).fetchone()
            if row: hotel_data = json.loads(row['data'])
            else: hotel_data = hotel_fallback
        else:
            hotel_data = hotel_fallback

        current_price = dynamic_context.get('price', 'N/A')
        check_in = dynamic_context.get('check_in', 'N/A')
        check_out = dynamic_context.get('check_out', 'N/A')
        hotel_data_str = json.dumps(hotel_data, indent=2, ensure_ascii=False)

        system_instruction = (
            f"You are a helpful AI assistant for hotel booking. Answer user questions based on this hotel data:\n"
            f"Price: {current_price} (Dates: {check_in}-{check_out}).\n"
            f"{hotel_data_str}\n"
            f"Reply in Vietnamese."
        )
        prompt = f"{system_instruction}\n\nUser: {user_message}"

        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        reply_text = response.text if response.text else "Xin lỗi, AI đang bận."

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post('/api/compare_ai')
def compare_ai_analysis():
    try:
        data = request.get_json()
        hotels = data.get('hotels', [])
        if len(hotels) < 2:
            return jsonify({'reply': "Cần ít nhất 2 khách sạn để so sánh."})

        prompt_content = "So sánh ngắn gọn các khách sạn sau:\n"
        for h in hotels:
            prompt_content += f"- {h['name']}: Giá {h.get('rate_per_night', {}).get('lowest', 'N/A')}, Rating {h.get('overall_rating', 'N/A')}.\n"

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_content + "\nTrả lời bằng tiếng Việt, ngắn gọn."
        )
        return jsonify({'reply': response.text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    db = database.get_db()
    rows = db.execute("""
        SELECT property_token, preview_data, visited_at 
        FROM recently_viewed 
        WHERE user_id = ? 
        ORDER BY visited_at DESC 
        LIMIT 20
    """, (session['user_id'],)).fetchall()
    
    history_list = []
    for row in rows:
        data = json.loads(row['preview_data'])
        data['property_token'] = row['property_token']
        history_list.append(data)
        
    return render_template('history.html', history_hotels=history_list)

# --- START BIG UPDATE (CHAT CONCIERGE WITH MEMORY & SMART PROMPT) ---

@app.route('/api/get_chat_history', methods=['GET'])
def get_chat_history():
    """Trả về lịch sử chat hiện tại trong session để hiển thị lại khi F5"""
    if 'chat_history' not in session:
        session['chat_history'] = []
    return jsonify(session['chat_history'])

@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    """Xóa lịch sử chat để bắt đầu lại"""
    session.pop('chat_history', None)
    return jsonify({"status": "cleared"})

@app.route('/api/chat_search', methods=['POST'])
def api_chat_search():
    """
    API Chatbot thông minh:
    - Biết gợi ý địa điểm nếu khách chưa biết đi đâu.
    - Không lặp lại câu hỏi như robot.
    - Chỉ Search khi đã chốt được tên thành phố.
    - JSON đầu ra được chuẩn hóa.
    """
    data = request.get_json()
    user_msg = data.get('message', '').strip()
    
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    if 'chat_history' not in session:
        session['chat_history'] = []
    
    history = session['chat_history']
    
    # Lấy context lịch sử (6 tin gần nhất)
    recent_history = history[-6:] 
    history_text = ""
    for msg in recent_history:
        role = "User" if msg['role'] == 'user' else "AI"
        content = msg['content']
        if msg.get('type') == 'search_result':
            content = "[Đã hiển thị danh sách khách sạn]"
        history_text += f"{role}: {content}\n"

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=gemini_api_key)

    # --- PROMPT ĐƯỢC NÂNG CẤP VÀ TỐI ƯU ---
    prompt = f"""
    Bạn là LigmaStay AI - Trợ lý đặt phòng khách sạn thông minh tại Việt Nam.

    QUY TẮC BẤT DI BẤT DỊCH:
    1. CHỈ TRẢ LỜI 1 JSON DUY NHẤT. KHÔNG ĐƯỢC VIẾT THÊM CHỮ NÀO BÊN NGOÀI JSON.
    2. KHÔNG DÙNG Markdown (```json). Chỉ trả về raw JSON string.

    CẤU TRÚC JSON MỤC TIÊU:
    {{
      "type": "chat" | "search",
      "city": "Tên thành phố (String) hoặc null",
      "price_range": "0-500000" | "500000-1000000" | "1000000-2000000" | "2000000+" | null,
      "rating": "4-5" | "3-5" | null,
      "amenities": ["Pool", "Free Wi-Fi", ...] (Mảng String, các từ khóa tiếng Anh: 'Pool', 'Fitness centre', 'Pet-friendly', 'Child-friendly', 'Free Wi-Fi', 'Air-conditioned') hoặc null,
      "reply_text": "Câu trả lời tiếng Việt"
    }}

    LỊCH SỬ HỘI THOẠI:
    {history_text}

    USER INPUT: "{user_msg}"

    -------------
    LOGIC XỬ LÝ:

    1. KIỂM TRA LẠC ĐỀ:
       - Nếu User hỏi chuyện KHÔNG LIÊN QUAN (code, toán, chính trị, tình cảm...):
         => "type": "chat", "reply_text": "Mình chỉ hỗ trợ tìm kiếm khách sạn và du lịch thôi ạ. Bạn cần tìm phòng ở đâu không?"

    2. XÁC ĐỊNH ĐỊA ĐIỂM (CITY):
       - Ưu tiên 1: Lấy trong User Input hiện tại (VD: "Đà Lạt", "đi SG", "Hà Nội").
       - Ưu tiên 2: Nếu Input không có, tìm ngược lại trong LỊCH SỬ.
       - Lưu ý:
         + Nếu User nhắc > 1 thành phố (VD: "Đà Nẵng hay Nha Trang?"): => "type": "chat", "city": null, "reply_text": "Gợi ý so sánh 2 nơi và hỏi user chốt nơi nào."
         + Chuẩn hóa tên: "SG"/"HCM" -> "Ho Chi Minh City", "Đà Lạt" -> "Da Lat".

    3. PHÂN LOẠI HÀNH ĐỘNG (TYPE):
       - Gán "type": "search" KHI VÀ CHỈ KHI:
         + Đã xác định được "city" (từ Input hoặc Lịch sử).
         + VÀ User thể hiện ý định tìm kiếm/đặt phòng/hỏi giá/hỏi tiện ích (VD: "tìm khách sạn", "giá bao nhiêu", "có phòng không", "ở đâu tốt", "có bể bơi không", "tìm đi", "ok chốt").
       
       - Gán "type": "chat" KHI:
         + Chưa có "city".
         + Hoặc User chỉ hỏi chung chung "đi đâu chơi", "gợi ý cho tôi", "nơi nào rẻ", "chỗ nào mát mẻ".
         => "reply_text": Gợi ý 2-3 địa điểm phù hợp context (Tuyệt đối TRÁNH lặp lại câu hỏi cũ 'Bạn định đi đâu' nếu user đang nhờ gợi ý). Hãy đóng vai hướng dẫn viên du lịch.

    4. TRÍCH XUẤT THAM SỐ (Chỉ khi type="search"):
       - price_range: Dựa vào con số user đưa. Nếu không rõ -> null.
       - rating: "4 sao", "sang trọng" -> "4-5"; "3 sao", "thoải mái" -> "3-5"; Khác -> null.
       - amenities: Map từ khóa sang tiếng Anh chuẩn: "Pool", "Fitness centre", "Pet-friendly", "Child-friendly", "Free Wi-Fi", "Air-conditioned".
         + Trả về dạng MẢNG (Array). Ví dụ: ["Pool", "Free Wi-Fi"]. Nếu không có -> null.

    5. REPLY_TEXT:
       - Nếu Search: "OK, mình tìm thấy vài nơi ở [City] theo ý bạn..."
       - Nếu Chat: Trả lời tự nhiên, thân thiện, gợi mở.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # Xử lý JSON từ AI (Clean kỹ hơn để tránh lỗi)
        json_str = response.text.strip()
        # Regex loại bỏ markdown code block nếu AI lỡ thêm vào
        json_str = re.sub(r"^```json|^```|```$", "", json_str, flags=re.MULTILINE).strip()
        
        parsed = json.loads(json_str)
        
        # Lưu tin nhắn User
        history.append({"role": "user", "content": user_msg})

        # XỬ LÝ LOGIC
        if parsed.get('type') == 'search':
            city = parsed.get('city')
            
            # Logic dự phòng: Nếu AI detect là search nhưng quên city (fallback)
            if not city:
                 for old_msg in reversed(history):
                     if old_msg.get('search_params', {}).get('city'):
                         city = old_msg['search_params']['city']
                         break
            
            if not city:
                 # Vẫn không có city -> Chuyển về chat để hỏi lại
                 reply = "Bạn muốn tìm khách sạn ở thành phố nào nhỉ?"
                 history.append({"role": "ai", "content": reply, "type": "chat"})
                 session.modified = True
                 return jsonify({"type": "chat", "reply_text": reply})

            # Gọi SerpAPI
            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)
            
            # amenities trả về là List, HotelSearchAPI hỗ trợ cả List và String
            hotels = search_api.search_hotels(
                city, 
                parsed.get('price_range'), 
                parsed.get('rating'), 
                parsed.get('amenities')
            )
            
            reply_text = parsed.get('reply_text', f"Kết quả tìm kiếm tại {city}:")
            
            history.append({
                "role": "ai", 
                "content": reply_text, 
                "type": "search_result",
                # Lưu params để context sau AI biết đang search ở đâu
                "search_params": {
                    "city": city,
                    "price_range": parsed.get('price_range'),
                    "amenities": parsed.get('amenities')
                }
            })
            session.modified = True 
            
            return jsonify({
                "type": "search_result",
                "reply_text": reply_text,
                "hotels": hotels
            })
            
        else:
            # Type = CHAT (Gợi ý địa điểm, chào hỏi, từ chối trả lời lạc đề...)
            reply_text = parsed.get('reply_text')
            history.append({"role": "ai", "content": reply_text, "type": "chat"})
            session.modified = True
            
            return jsonify({
                "type": "chat",
                "reply_text": reply_text
            })

    except Exception as e:
        print(f"Chat Error: {e}")
        # Trả về lỗi thân thiện
        return jsonify({
            "type": "chat",
            "reply_text": "Xin lỗi, server đang bận xíu. Bạn thử lại sau nhé!"
        })

# --- END BIG UPDATE ---

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    app.run(debug=True)
