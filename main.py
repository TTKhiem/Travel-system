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
from collections import Counter

from hotel_search import HotelSearchAPI
import database
from PIL import Image
import io

# Load API key lưu trong .env
load_dotenv()

app = Flask(__name__)
app.config['DATABASE'] = database.DATABASE
app.secret_key = os.getenv('APP_SECRET')
database.init_app(app)

def get_user_recent_city(user_id):
    """Phân tích lịch sử xem phòng để tìm thành phố user quan tâm nhất"""
    db = database.get_db()
    
    # 1. Lấy dữ liệu preview của 10 khách sạn xem gần nhất
    rows = db.execute("""
        SELECT preview_data 
        FROM recently_viewed 
        WHERE user_id = ? 
        ORDER BY visited_at DESC 
        LIMIT 10
    """, (user_id,)).fetchall()
    
    if not rows:
        return None
        
    cities_found = []
    
    # Danh sách từ khóa để map địa chỉ sang tên thành phố chuẩn
    # Key: Từ khóa trong địa chỉ (viết thường) -> Value: Tên chuẩn trong DB/Select box
    city_mapping = {
        "hà nội": "Hà Nội", "hanoi": "Hà Nội", "ha noi": "Hà Nội",
        "đà nẵng": "Đà Nẵng", "da nang": "Đà Nẵng",
        "hồ chí minh": "TP. Hồ Chí Minh", "ho chi minh": "TP. Hồ Chí Minh", "sai gon": "TP. Hồ Chí Minh",
        "đà lạt": "Đà Lạt", "da lat": "Đà Lạt",
        "nha trang": "Nha Trang",
        "huế": "Huế", "hue": "Huế",
        "sa pa": "Sa Pa", "sapa": "Sa Pa",
        "phú quốc": "Phú Quốc", "phu quoc": "Phú Quốc",
        "vũng tàu": "Vũng Tàu", "vung tau": "Vũng Tàu"
    }
    
    for row in rows:
        try:
            data = json.loads(row['preview_data'])
            address = data.get('address', '').lower()
            
            # Kiểm tra xem địa chỉ chứa từ khóa thành phố nào
            for key, val in city_mapping.items():
                if key in address:
                    cities_found.append(val)
                    break # Tìm thấy 1 thành phố thì dừng, chuyển sang khách sạn tiếp theo
        except:
            continue
            
    if not cities_found:
        return None
        
    # 2. Trả về thành phố xuất hiện nhiều nhất (Most Common)
    # Counter(cities_found).most_common(1) trả về [('Đà Nẵng', 3)]
    most_common = Counter(cities_found).most_common(1)
    return most_common[0][0] if most_common else None

def analyze_vibe_from_amenities(amenities_list):
    # Định nghĩa từ khóa cho từng Vibe
    vibe_keywords = {
        'healing': ['spa', 'massage', 'yoga', 'garden', 'meditation', 'sauna', 'steam room', 'hot tub'],
        'adventure': ['fitness', 'gym', 'hiking', 'diving', 'bike', 'canoe', 'windsurfing'],
        'luxury': ['butler', 'limousine', 'infinity pool', 'wine', 'champagne', 'club'],
        'business': ['meeting', 'conference', 'business centre', 'printer', 'fax']
    }
    
    # Chuẩn hóa amenities đầu vào thành chữ thường
    am_text = " ".join([str(a).lower() for a in amenities_list])
    scores = {k: 0 for k in vibe_keywords}
    
    # Chấm điểm
    for vibe, keywords in vibe_keywords.items():
        for kw in keywords:
            if kw in am_text:
                scores[vibe] += 1
                
    # Tìm vibe có điểm cao nhất
    best_vibe = max(scores, key=scores.get)
    # Chỉ trả về nếu điểm >= 2 (tức là khách sạn này thể hiện rõ vibe đó)
    if scores[best_vibe] >= 2:
        return best_vibe
    return None

@app.context_processor
def inject_user():
    user_data = None
    if 'user_id' in session:
        db = database.get_db()
        row = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        if row:
            user_data = dict(row)
            if user_data.get('preferences'):
                try:
                    user_data['preferences_dict'] = json.loads(user_data['preferences'])
                except:
                    user_data['preferences_dict'] = {}
            else:
                user_data['preferences_dict'] = {}
    
    return dict(user=user_data)

def generate_ai_suggestion(user_prefs, history_city=None):
    # Tạo gợi ý cá nhân hóa. Ưu tiên History City > Random theo Vibe
    
    if not user_prefs:
        return None
    
    vibe = user_prefs.get('vibe', 'adventure')
    budget = user_prefs.get('budget', 'mid')
    
    # Map vibe sang icon và lời chào
    vibe_config = {
        'healing': {
            'icon': '🌿',
            'greetings': [
                'Không gian yên tĩnh để chữa lành tâm hồn',
                'Tìm về thiên nhiên, bỏ lại âu lo',
                'Nghỉ dưỡng thư thái, tái tạo năng lượng'
            ]
        },
        'adventure': {
            'icon': '🎒',
            'greetings': [
                'Sẵn sàng cho chuyến khám phá tiếp theo chưa?',
                'Những trải nghiệm mới đang chờ đón bạn',
                'Xách balo lên và đi thôi!'
            ]
        },
        'luxury': {
            'icon': '💎',
            'greetings': [
                'Trải nghiệm đẳng cấp thượng lưu',
                'Kỳ nghỉ sang trọng xứng tầm với bạn',
                'Tận hưởng dịch vụ 5 sao hoàn hảo'
            ]
        },
        'business': {
            'icon': '💼',
            'greetings': [
                'Tiện nghi tối ưu cho chuyến công tác',
                'Kết nối thành công, nghỉ ngơi trọn vẹn',
                'Không gian làm việc chuyên nghiệp'
            ]
        }
    }
    
    # Fallback cities nếu không có history (Random theo Vibe cũ)
    fallback_cities = {
        'healing': ['Đà Lạt', 'Sa Pa', 'Huế'],
        'adventure': ['Đà Nẵng', 'Nha Trang', 'Sa Pa'],
        'luxury': ['Phú Quốc', 'Đà Nẵng', 'TP. Hồ Chí Minh'],
        'business': ['TP. Hồ Chí Minh', 'Hà Nội', 'Đà Nẵng']
    }

    config = vibe_config.get(vibe, vibe_config['adventure'])
    
    # --- LOGIC QUYẾT ĐỊNH THÀNH PHỐ ---
    import random
    
    if history_city:
        city = history_city
        # Nếu có lịch sử, đổi lời chào cho phù hợp ngữ cảnh "Quay lại"
        greeting = f"Tiếp tục kế hoạch vi vu tại {city} nhé?"
    else:
        # Nếu không có lịch sử, random theo vibe
        city_list = fallback_cities.get(vibe, fallback_cities['adventure'])
        city = random.choice(city_list)
        greeting = random.choice(config['greetings'])
    
    # Map budget sang price_range
    budget_map = {
        'low': '0-500000',
        'mid': '1000000-2000000',
        'high': '2000000+'
    }
    price_range = budget_map.get(budget, '1000000-2000000')
    
    return {
        'city': city,
        'price_range': price_range,
        'vibe_icon': config['icon'],
        'greeting': greeting
    }

@app.route('/')
def home():
    user_data = None
    ai_suggestion = None
    
    if 'user_id' in session:
        db = database.get_db()
        user_data = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('index.html', user=user_data, form_type='login', ai_suggestion=None)

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
        # Thêm preferences mặc định là NULL (hoặc '{}' nếu muốn)
        cursor = db.execute("INSERT INTO users (username, password, preferences) VALUES (?, ?, ?)",
                (username, hashed_pw, None))
        user_id = cursor.lastrowid
        db.commit()
        flash("✅ Account created successfully! Please log in.")
        return redirect(url_for('home'))
    except sqlite3.IntegrityError:
        flash("❌ Username already exists.")
        return redirect(url_for('register_page'))
    except Exception as e:
        print(f"Registration error: {e}")
        flash(f"❌ Có lỗi xảy ra: {str(e)}")
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
        
    # Dữ liệu từ forms
    price_range = request.form.get('price_range')
    rating_range = request.form.get('rating')
    amenities = request.form.getlist('amenities') 
    # Track trường dữ liệu nào được filled bởi user_preferences - filled bởi AI cho vui :p
    auto_filled_items = []
    
    if 'user_id' in session:
        db = database.get_db()
        user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
        
        if user and user['preferences']:
            try:
                prefs = json.loads(user['preferences'])
                vibe = prefs.get('vibe', '')
                budget = prefs.get('budget', '')
                companion = prefs.get('companion', '')

                if not price_range:
                    if budget == 'low':
                        price_range = '0-500000'
                        auto_filled_items.append('price')
                    elif budget == 'mid':
                        price_range = '500000-2000000'
                        auto_filled_items.append('price')
                    else:
                        price_range = '2000000+'
                        auto_filled_items.append('price')
                
                # A. Tự động điền Hạng sao (Map khớp với rating_mapping trong hotel_search.py)
                if not rating_range:
                    if vibe == 'luxury': 
                        rating_range = '4-5'
                        auto_filled_items.append('rating')
                    else:
                        rating_range = '3-5'
                        auto_filled_items.append('rating')
                
                # B. Tự động điền Tiện nghi (Map khớp với amenities_mapping trong hotel_search.py)
                # Chỉ thêm nếu user chưa chọn gì để tránh làm loãng kết quả
                if not amenities:
                    if vibe == 'healing': 
                        amenities.append('Pool') # Map với ID '5'
                        is_auto_filled = True
                        auto_filled_items.append('Pool')
                    elif vibe == 'adventure':
                        amenities.append('Fitness centre') # Map với ID '7'
                        auto_filled_items.append('Fitness centre')
                    elif companion == 'family':
                        amenities.append('Child-friendly') # Map với ID '12'
                        auto_filled_items.append('Child-friendly')
                    elif companion == 'couple':
                        amenities.append('Bar') # Map với ID '15'
                        auto_filled_items.append('Bar')
                    else:
                        amenities.append('Free Wi-Fi')
                        auto_filled_items.append('Free Wi-Fi')

            except Exception as e:
                print(f"Auto-fill Error: {e}")

    # --- 3. GỌI API (VỚI THAM SỐ ĐÃ ĐƯỢC AUTO-FILL) ---
    try:
        serp_api_key = os.getenv("SERPAPI_KEY")
        search_api = HotelSearchAPI(serp_api_key)
        search_results = search_api.search_hotels(city, price_range, rating_range, amenities)
        
        # --- 4. HYBRID: SMART RANKING (SẮP XẾP LẠI KẾT QUẢ) ---
        if search_results and user and user['preferences']:
            try:
                prefs = json.loads(user['preferences'])
                vibe = prefs.get('vibe', '')
                companion = prefs.get('companion', '')
                
                for hotel in search_results:
                    score = 0
                    
                    # Chuẩn hóa tiện nghi của khách sạn trả về từ API để so sánh
                    am_list = []
                    raw_ams = hotel.get('amenities', [])
                    for a in raw_ams:
                        # API Google trả về có thể là string hoặc dict
                        am_name = a if isinstance(a, str) else a.get('name', '')
                        am_list.append(am_name.lower())
                    am_str = " ".join(am_list)
                    
                    rating = hotel.get('overall_rating', 0)
                    
                    # --- LOGIC CHẤM ĐIỂM THEO VIBE---
                    if vibe == 'luxury':
                        if rating >= 4.5: score += 50
                        if 'pool' in am_str or 'spa' in am_str: score += 20
                    elif vibe == 'healing':
                        if 'spa' in am_str or 'garden' in am_str or 'pool' in am_str: score += 40
                        if 'beach' in am_str or 'view' in am_str: score += 20
                    elif vibe == 'adventure':
                        if 'fitness' in am_str or 'gym' in am_str: score += 30
                    elif vibe == 'business':
                        if 'wi-fi' in am_str or 'wifi' in am_str or 'desk' in am_str: score += 40
                    # Lưu điểm
                    hotel['match_score'] = score

                # Sắp xếp: Điểm cao nhất lên đầu
                search_results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
                if search_results and search_results[0].get('match_score', 0) > 0:
                    search_results[0]['is_best_match'] = True
                    
            except Exception as e:
                print(f"Ranking Error: {e}")

        return render_template('hotel_results.html', 
                               hotels=search_results,
                               search_params={
                                   'city': city,
                                   'price_range': price_range,
                                   'rating_range': rating_range,
                                   'amenities': amenities
                               },
                               auto_filled_items=auto_filled_items) # Báo cho template biết
                               
    except Exception as e:
        print(f"Search Process Error: {e}")
        return render_template('hotel_results.html', hotels=[], error=f"Lỗi: {str(e)}")
    
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
            
            check_exist = db.execute("SELECT 1 FROM recently_viewed WHERE user_id=? AND property_token=?", (session['user_id'], property_token)).fetchone()
            
            if check_exist:
                db.execute(
                    "UPDATE recently_viewed SET visited_at = CURRENT_TIMESTAMP, preview_data = ? WHERE user_id = ? AND property_token = ?",
                    (preview_json, session['user_id'], property_token)
                )
            else:
                db.execute(
                    "INSERT INTO recently_viewed (user_id, property_token, preview_data, visited_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                    (session['user_id'], property_token, preview_json)
                )
            db.commit()
        except Exception as e:
            print(f"Lỗi lưu lịch sử: {e}")

    if not hotel_data:
        return render_template('hotel_detail.html', error="Không tìm thấy khách sạn.")
    
    match_reason = None
    if 'user_id' in session:
        user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
        # Check xem đã cache lý do chưa (trong bảng recently_viewed)
        recent_entry = db.execute("SELECT match_reason FROM recently_viewed WHERE user_id=? AND property_token=?", (session['user_id'], property_token)).fetchone()
        
        if recent_entry and recent_entry['match_reason']:
            match_reason = recent_entry['match_reason'] # Dùng Cache
    # Test khả năng học theo giá của người dùng - testing
    if 'user_id' in session:
        user_db = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
        current_prefs = json.loads(user_db['preferences']) if user_db and user_db['preferences'] else {}
        
        # Học về budget của người dùng
        try:
            price_str = hotel_data.get('rate_per_night', {}).get('lowest', '0')
            price_num = int(re.sub(r'[^\d]', '', str(price_str)))
            
            if price_num > 1800000: 
                # Tăng biến đếm trong session
                session['expensive_view_count'] = session.get('expensive_view_count', 0) + 1
                # Nếu xem 3 lần khách sạn đắt tiền thì sẽ nâng hạng Budget
                if session['expensive_view_count'] >= 3:
                    if current_prefs.get('budget') != 'high':
                        current_prefs['budget'] = 'high'
                        db.execute("UPDATE users SET preferences = ? WHERE id = ?", (json.dumps(current_prefs), session['user_id']))
                        db.commit()
                        print(f"✨ Passive Learning: Đã nâng cấp user lên HIGH budget.")
                        session['expensive_view_count'] = 0 # Reset
        except Exception as e:
            print(f"Budget Learning Error: {e}")

        # Học theo amenities của khách sạn => vibe của người dùng ?
        try:
            # Lấy danh sách tiện nghi khách sạn hiện tại
            raw_amenities = []
            if hotel_data.get('amenities'):
                for a in hotel_data['amenities']:
                    # Xử lý nếu API trả về dict hoặc string
                    val = a.get('name') if isinstance(a, dict) else a
                    raw_amenities.append(val)
            
            # Phân tích vibe của khách sạn này
            detected_vibe = analyze_vibe_from_amenities(raw_amenities)
            if detected_vibe:
                # Lưu vào session dạng: session['vibe_tracker'] = {'healing': 1, 'adventure': 0, ...}
                if 'vibe_tracker' not in session:
                    session['vibe_tracker'] = {}
                
                current_score = session['vibe_tracker'].get(detected_vibe, 0) + 1
                session['vibe_tracker'][detected_vibe] = current_score
                session.modified = True # Báo cho Flask biết session đã thay đổi
                print(f"👁 User viewing {detected_vibe} hotel. Score: {current_score}")
                #: Nếu xem 4 khách sạn cùng vibe sẽ update lại 1 lần
                if current_score >= 4:
                    # Chỉ update nếu vibe hiện tại khác với cái đang học được
                    if current_prefs.get('vibe') != detected_vibe:
                        current_prefs['vibe'] = detected_vibe
                        # Cập nhật DB
                        db.execute("UPDATE users SET preferences = ? WHERE id = ?", (json.dumps(current_prefs), session['user_id']))
                        db.commit()
                        print(f"✨ Passive Learning: Đã đổi Vibe user sang {detected_vibe.upper()} dựa trên hành vi.")
                        # Reset tracker để tránh update liên tục
                        session['vibe_tracker'] = {} 

        except Exception as e:
            print(f"Vibe Learning Error: {e}")
    
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
            
    return render_template("hotel_detail.html", match_reason = match_reason, hotel=hotel_data, local_reviews=local_reviews, is_favorite=is_favorite)

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
        db.execute("DELETE FROM review_summaries WHERE property_token = ?", (property_token,))
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

        # --- 1. KIỂM TRA CACHE TRONG DB ---
        cached = db.execute(
            "SELECT summary_content, updated_at FROM review_summaries WHERE property_token = ?",
            (property_token,)
        ).fetchone()

        # Nếu có cache và chưa quá 24 giờ -> Dùng lại luôn
        if cached and cached['summary_content']:
            # Thêm try-catch để parse thời gian an toàn
            try:
                last_update = datetime.strptime(cached['updated_at'], '%Y-%m-%d %H:%M:%S')
                # Dùng utcnow() để so khớp với SQLite CURRENT_TIMESTAMP (thường là UTC)
                if datetime.utcnow() - last_update < timedelta(hours=24):
                    print(f"Using cached summary for {property_token}")
                    return jsonify({'summary': cached['summary_content']})
            except Exception as e:
                print(f"Date parse error: {e}")
        # --- 2. NẾU KHÔNG CÓ HOẶC CŨ -> GỌI AI ---
        print(f"Generating NEW summary for {property_token}")
        
        # Lấy review từ DB
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
        new_summary = response.text
        db.execute(
            "INSERT OR REPLACE INTO review_summaries (property_token, summary_content, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (property_token, new_summary)
        )
        db.commit()

        return jsonify({'summary': new_summary})

    except Exception as e:
        print(f"Summary Error: {e}")
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

        # --- LẤY PREFERENCES CỦA USER ---
        user_prefs_context = ""
        if 'user_id' in session:
            db = database.get_db()
            user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
            if user and user['preferences']:
                prefs = json.loads(user['preferences'])
                vibe_map = {
                    'healing': '🌿 Chữa lành (yên tĩnh, spa)',
                    'adventure': '🎒 Khám phá (hoạt động ngoài trời)',
                    'luxury': '💎 Sang chảnh (5 sao)',
                    'business': '💼 Công tác'
                }
                user_prefs_context = f"""
                THÔNG TIN SỞ THÍCH CỦA USER:
                - Phong cách: {vibe_map.get(prefs.get('vibe'), prefs.get('vibe', 'N/A'))}
                - Đi cùng: {prefs.get('companion', 'N/A')}
                - Ngân sách: {prefs.get('budget', 'N/A')}
                
                LƯU Ý: Khi tư vấn, hãy nhấn mạnh các điểm phù hợp với sở thích của user.
                Ví dụ: Nếu user thích "healing" và khách sạn có Spa -> nhấn mạnh Spa.
                """

        current_price = dynamic_context.get('price', 'N/A')
        check_in = dynamic_context.get('check_in', 'N/A')
        check_out = dynamic_context.get('check_out', 'N/A')
        hotel_data_str = json.dumps(hotel_data, indent=2, ensure_ascii=False)

        system_instruction = (
            f"You are a helpful AI assistant for hotel booking. Answer user questions based on this hotel data:\n"
            f"Price: {current_price} (Dates: {check_in}-{check_out}).\n"
            f"{hotel_data_str}\n"
            f"{user_prefs_context}"
            f"Reply in Vietnamese, friendly and personalized based on user preferences if available."
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

@app.route('/api/get_chat_history', methods=['GET'])
def get_chat_history():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return jsonify(session['chat_history'])

@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    session.pop('chat_history', None)
    return jsonify({"status": "cleared"})

@app.route('/api/chat_search', methods=['POST'])
def api_chat_search():
    """
    API Chatbot thông minh
    - Logic Prompt tối ưu: Phân loại Chat/Search, chuẩn hóa amenities, xử lý logic fallback City.
    - Tối ưu Session: Chỉ lưu danh sách khách sạn rút gọn (Lite) vào lịch sử để tránh lỗi tràn cookie.
    """
    data = request.get_json()
    user_msg = data.get('message', '').strip()
    page_context = data.get('page_context', {}) # Danh sách khách sạn đang xem
    
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
        # Nếu tin nhắn cũ là kết quả search, thay thế nội dung dài dòng bằng placeholder
        if msg.get('type') == 'search_result':
            content = "[Đã hiển thị danh sách khách sạn]"
        history_text += f"{role}: {content}\n"

    # --- LẤY PREFERENCES CỦA USER (NẾU CÓ) ---
    user_prefs = None
    if 'user_id' in session:
        db = database.get_db()
        user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
        if user and user['preferences']:
            user_prefs = json.loads(user['preferences'])

    # Lấy dữ liệu khách sạn đang xem và tạo context cho prompt 
    current_view_context = ""
    if page_context and page_context.get('hotels'):
        hotel_list_str = "\n".join([
            f"- {h['name']}:\n   + Giá: {h['price']}\n   + Đánh giá: {h['rating']}/5\n   + Tiện nghi: {h.get('amenities', 'Không rõ')}"
            for h in page_context['hotels']
        ])
        current_view_context = f"""
        THÔNG TIN TRANG HIỆN TẠI NGƯỜI DÙNG ĐANG XEM:
        Người dùng đang đứng ở trang kết quả tìm kiếm. Dưới đây là danh sách các khách sạn đang hiển thị trên màn hình:
        {hotel_list_str}
        
        NHIỆM VỤ:
        1. So sánh: Nếu user hỏi "cái nào có hồ bơi", "cái nào tiện nghi nhất", hãy DÙNG DỮ LIỆU "Tiện nghi" ở trên để trả lời chính xác.
        2. Tư vấn giá: Dùng dữ liệu "Giá" để so sánh đắt/rẻ.
        3. Tuyệt đối không bịa đặt tiện nghi nếu trong danh sách không ghi (hãy nói là "thông tin chưa đề cập").
        """
    
    # Tạo context preferences cho prompt
    prefs_context = ""
    if user_prefs:
        vibe_map = {
            'healing': '🌿 Chữa lành (yên tĩnh, spa, thiên nhiên)',
            'adventure': '🎒 Khám phá (hoạt động ngoài trời, thể thao)',
            'luxury': '💎 Sang chảnh (5 sao, dịch vụ cao cấp)',
            'business': '💼 Công tác (Wi-Fi tốt, vị trí trung tâm)'
        }
        companion_map = {
            'solo': 'Một mình',
            'couple': 'Cặp đôi',
            'family': 'Gia đình',
            'friends': 'Nhóm bạn'
        }
        budget_map = {
            'low': '< 500k/đêm',
            'mid': '500k - 2tr/đêm',
            'high': '> 2tr/đêm'
        }
        
        prefs_context = f"""
    THÔNG TIN SỞ THÍCH CỦA USER (Ưu tiên sử dụng khi user không chỉ định rõ):
    - Phong cách: {vibe_map.get(user_prefs.get('vibe'), user_prefs.get('vibe', 'N/A'))}
    - Đi cùng: {companion_map.get(user_prefs.get('companion'), user_prefs.get('companion', 'N/A'))}
    - Ngân sách: {budget_map.get(user_prefs.get('budget'), user_prefs.get('budget', 'N/A'))}
    
    LƯU Ý: Khi user tìm kiếm mà KHÔNG chỉ định amenities/price, hãy TỰ ĐỘNG thêm vào dựa trên preferences:
    - Vibe "healing" -> amenities: ["Spa", "Mountain View"] hoặc tương tự
    - Vibe "adventure" -> amenities: ["Fitness centre", "Pool"]
    - Vibe "luxury" -> rating: "4-5", amenities: ["Pool", "Fitness centre"]
    - Companion "family" -> amenities: ["Child-friendly", "Pool"]
    - Budget "high" -> price_range: "2000000+"
    - Budget "low" -> price_range: "0-500000"
    """

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=gemini_api_key)

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

    {prefs_context}

    {current_view_context}

    LỊCH SỬ HỘI THOẠI:
    {history_text}

    USER INPUT: "{user_msg}"

    -------------
    LOGIC XỬ LÝ:

    1. KIỂM TRA LẠC ĐỀ:
       - Nếu User hỏi chuyện KHÔNG LIÊN QUAN (code, toán, chính trị...):
         => "type": "chat", "reply_text": "Mình chỉ hỗ trợ tìm kiếm khách sạn và du lịch thôi ạ. Bạn cần tìm phòng ở đâu không?"

    2. XÁC ĐỊNH ĐỊA ĐIỂM (CITY):
       - Ưu tiên 1: Lấy trong User Input hiện tại.
       - Ưu tiên 2: Nếu Input không có, tìm ngược lại trong LỊCH SỬ.
       - Lưu ý: Chuẩn hóa tên: "SG"/"HCM" -> "Ho Chi Minh City", "Đà Lạt" -> "Da Lat".

    3. PHÂN LOẠI HÀNH ĐỘNG (TYPE):
       - Gán "type": "search" KHI VÀ CHỈ KHI:
         + Đã xác định được "city".
         + VÀ User thể hiện ý định tìm kiếm/đặt phòng/hỏi giá/tiện ích.
       
       - Gán "type": "chat" KHI:
         + Chưa có "city".
         + Hoặc User chỉ hỏi chung chung "đi đâu chơi", "gợi ý cho tôi".
         => "reply_text": Gợi ý 2-3 địa điểm phù hợp context.

    4. TRÍCH XUẤT THAM SỐ (Chỉ khi type="search"):
       - price_range: Dựa vào con số user đưa.
       - rating: "4 sao" -> "4-5", "3 sao" -> "3-5".
       - amenities: Map từ khóa sang tiếng Anh chuẩn (Pool, Free Wi-Fi...). Trả về MẢNG.

    5. REPLY_TEXT:
       - Nếu Search: "OK, mình tìm thấy vài nơi ở [City] theo ý bạn..."
       - Nếu Chat: Trả lời tự nhiên, thân thiện.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # Xử lý JSON từ AI
        json_str = response.text.strip()
        json_str = re.sub(r"^```json|^```|```$", "", json_str, flags=re.MULTILINE).strip()
        
        parsed = json.loads(json_str)
        
        # Lưu tin nhắn User vào lịch sử
        history.append({"role": "user", "content": user_msg})

        # --- LOGIC XỬ LÝ ---
        if parsed.get('type') == 'search':
            city = parsed.get('city')
            
            # Logic dự phòng: Nếu AI quên city, tìm lại trong lịch sử cũ (Từ Code 1)
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

            # --- TỰ ĐỘNG THÊM PREFERENCES NẾU USER KHÔNG CHỈ ĐỊNH RÕ ---
            price_range = parsed.get('price_range')
            rating = parsed.get('rating')
            amenities = parsed.get('amenities') or []
            
            # Nếu user có preferences và chưa chỉ định rõ, tự động thêm
            if user_prefs:
                # Thêm price_range từ preferences nếu chưa có
                if not price_range:
                    budget = user_prefs.get('budget')
                    if budget == 'low':
                        price_range = '0-500000'
                    elif budget == 'mid':
                        price_range = '1000000-2000000'
                    elif budget == 'high':
                        price_range = '2000000+'
                
                # Thêm rating từ vibe nếu chưa có
                if not rating:
                    vibe = user_prefs.get('vibe')
                    if vibe == 'luxury':
                        rating = '4-5'
                
                # Thêm amenities từ preferences nếu chưa có hoặc ít
                if len(amenities) == 0:
                    vibe = user_prefs.get('vibe')
                    companion = user_prefs.get('companion')
                    
                    if vibe == 'healing':
                        amenities.extend(['Pool'])  # Có thể thêm Spa nếu API hỗ trợ
                    elif vibe == 'adventure':
                        amenities.extend(['Fitness centre', 'Pool'])
                    elif vibe == 'luxury':
                        amenities.extend(['Pool', 'Fitness centre'])
                    
                    if companion == 'family':
                        if 'Child-friendly' not in amenities:
                            amenities.append('Child-friendly')
                        if 'Pool' not in amenities:
                            amenities.append('Pool')
                    elif companion == 'couple':
                        if 'Pool' not in amenities:
                            amenities.append('Pool')

            # Gọi SerpAPI
            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)
            
            hotels = search_api.search_hotels(
                city, 
                price_range, 
                rating, 
                amenities if len(amenities) > 0 else None
            )
            
            # --- TỐI ƯU SESSION (Quan trọng từ Code 2) ---
            # Chỉ lưu danh sách rút gọn vào Session để tránh lỗi Cookie too large
            hotels_lite = []
            if hotels:
                # Chỉ lưu tối đa 4 khách sạn đầu tiên vào lịch sử
                for h in hotels[:4]:
                    hotels_lite.append({
                        "name": h.get('name'),
                        "property_token": h.get('property_token'),
                        "rate_per_night": h.get('rate_per_night'),
                        "overall_rating": h.get('overall_rating'),
                        # Chỉ lưu 1 ảnh thumb nhỏ gọn
                        "images": [{"original_image": h['images'][0]['original_image']}] if h.get('images') else []
                    })

            reply_text = parsed.get('reply_text', f"Kết quả tìm kiếm tại {city}:")
            
            # Lưu vào lịch sử (Lưu hotels_lite thay vì full hotels)
            history.append({
                "role": "ai", 
                "content": reply_text, 
                "type": "search_result",
                "search_params": {
                    "city": city,
                    "price_range": parsed.get('price_range'),
                    "amenities": parsed.get('amenities')
                },
                "hotels": hotels_lite  # <--- Lưu bản rút gọn
            })
            session.modified = True 
            
            # Trả về JSON cho Client (Trả về full hotels để hiển thị đẹp)
            return jsonify({
                "type": "search_result",
                "reply_text": reply_text,
                "hotels": hotels 
            })
            
        else:
            # Type = CHAT (Code 1 Logic)
            reply_text = parsed.get('reply_text')
            history.append({"role": "ai", "content": reply_text, "type": "chat"})
            session.modified = True
            
            return jsonify({
                "type": "chat",
                "reply_text": reply_text
            })

    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({
            "type": "chat",
            "reply_text": "Xin lỗi, server đang bận xíu. Bạn thử lại sau nhé!"
        })
    
# API Lưu sở thích từ Modal (Ngay trang Home - index.html)
@app.route('/api/update_preferences', methods=['POST'])
def update_preferences():
    # 1. Kiểm tra đăng nhập
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # 2. Lấy dữ liệu từ Frontend gửi lên (companion, vibe, budget)
        data = request.get_json()
        
        # 3. Chuyển thành chuỗi JSON để lưu vào cột 'preferences' trong DB
        prefs_json = json.dumps(data)
        
        db = database.get_db()
        db.execute(
            "UPDATE users SET preferences = ? WHERE id = ?", 
            (prefs_json, session['user_id'])
        )
        db.commit()
        
        return jsonify({'message': 'Success'}), 200
        
    except Exception as e:
        print(f"Update Prefs Error: {e}")
        return jsonify({'error': str(e)}), 500

# 2. Lấy Match Reason cho Hotel Detail (Async)
@app.route('/api/get_match_reason', methods=['POST'])
def get_match_reason_api():
    if 'user_id' not in session:
        return jsonify({'match': None})
        
    data = request.get_json()
    property_token = data.get('property_token')
    hotel_name = data.get('hotel_name')
    amenities = data.get('amenities', []) # List string
    
    db = database.get_db()
    
    # Check Cache trong DB trước
    recent = db.execute("SELECT match_reason FROM recently_viewed WHERE user_id=? AND property_token=?", 
                       (session['user_id'], property_token)).fetchone()
    
    if recent and recent['match_reason']:
        return jsonify({'match': recent['match_reason']})
        
    # Nếu chưa có cache -> Gọi Gemini
    user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
    if user and user['preferences']:
        prefs = json.loads(user['preferences'])
        
        prompt = f"""
        User Prefer: {json.dumps(prefs)}. 
        Hotel: {hotel_name}, Amenities: {str(amenities[:10])}.
        Task: 
        1. Calculate match score (0-100%).
        2. Write ONE short sentence explaining WHY in Vietnamese.
        Format: "Score|Sentence"
        """
        try:
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            client = genai.Client(api_key=gemini_api_key)           
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            match_reason = response.text.strip()
            
            # Lưu cache để lần sau không phải gọi lại
            db.execute("UPDATE recently_viewed SET match_reason = ? WHERE user_id=? AND property_token=?", 
                      (match_reason, session['user_id'], property_token))
            db.commit()
            
            return jsonify({'match': match_reason})
        except Exception as e:
            print(f"Match API Error: {e}")
            return jsonify({'match': None})
            
    return jsonify({'match': None})

@app.route('/api/get_home_suggestion', methods=['GET'])
def get_home_suggestion_api():
    # 1. Nếu chưa đăng nhập
    if 'user_id' not in session:
        return jsonify({'suggestion': None, 'is_logged_in': False})
    
    # 2. Nếu đã đăng nhập
    db = database.get_db()
    user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    suggestion = None
    if user and user['preferences']:
        try:
            prefs = json.loads(user['preferences'])
            recent_city = get_user_recent_city(session['user_id'])
            suggestion = generate_ai_suggestion(prefs, history_city=recent_city)
            
        except Exception as e:
            print(f"Error generating suggestion: {e}")
            # Fallback nếu lỗi
            suggestion = generate_ai_suggestion(prefs)
            
    return jsonify({'suggestion': suggestion, 'is_logged_in': True})

def clean_json_text(text):
    """Làm sạch chuỗi JSON trả về từ AI (xóa markdown ```json)"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE)
    return text.strip()

@app.route('/api/generate_itinerary', methods=['POST'])
def generate_itinerary():
    try:
        data = request.get_json()
        token = data.get('property_token')
        hotel_name = data.get('hotel_name')
        address = data.get('address')
        
        # 1. Xác định Vibe của user (Nếu chưa login thì mặc định là 'adventure')
        vibe = 'adventure' 
        if 'user_id' in session:
            db = database.get_db()
            user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
            if user and user['preferences']:
                prefs = json.loads(user['preferences'])
                vibe = prefs.get('vibe', 'adventure')
        
        # 2. Kiểm tra Cache (Tiết kiệm tiền API & Tăng tốc độ)
        db = database.get_db()
        cached = db.execute(
            "SELECT itinerary_json FROM hotel_itineraries WHERE property_token=? AND vibe=?", 
            (token, vibe)
        ).fetchone()
        
        if cached:
            print(f"🎯 Trip Genie: Hit Cache for {token} - {vibe}")
            return jsonify(json.loads(cached['itinerary_json']))
        
        hotel_cache_row = db.execute("SELECT data FROM hotel_cache WHERE token = ?", (token,)).fetchone()
        
        # Bổ sung thông tin về nearby_places => Tránh bịa thông tin không có thật
        real_places_context = ""
        if hotel_cache_row:
            hotel_data = json.loads(hotel_cache_row['data'])
            nearby_list = hotel_data.get('nearby_places', [])
            
            # Chỉ lấy khoảng 15 địa điểm đầu tiên để đưa vào prompt (tránh quá dài)
            if nearby_list:
                places_str = "\n".join([f"- {p['name']} ({p.get('transportations', [{'duration': 'Gần'}])[0]['duration']})" for p in nearby_list[:15]])
                real_places_context = f"""
                DANH SÁCH ĐỊA ĐIỂM CÓ THẬT XUNG QUANH KHÁCH SẠN (Ưu tiên tuyệt đối sử dụng các địa điểm này):
                {places_str}
                """

        # 3. Nếu chưa có Cache -> Gọi Gemini AI
        print(f"🤖 Trip Genie: Calling AI for {token} - {vibe}")
        
        vibe_desc = {
            'healing': 'thư giãn, yên tĩnh, spa, thiên nhiên, không xô bồ',
            'adventure': 'khám phá, vận động, trải nghiệm địa phương độc lạ',
            'luxury': 'sang trọng, check-in đẳng cấp, fine dining, dịch vụ 5 sao',
            'business': 'tiện lợi, cafe làm việc, thư giãn nhẹ nhàng buổi tối'
        }
        user_vibe_detail = vibe_desc.get(vibe, 'cân bằng')

        prompt = f"""
        Đóng vai một hướng dẫn viên du lịch địa phương sành sỏi (Trip Genie).
        
        THÔNG TIN:
        - Khách sạn xuất phát: {hotel_name}
        - Địa chỉ: {address}
        - Phong cách khách du lịch (Vibe): "{vibe}" (Ưu tiên: {user_vibe_detail}).

        {real_places_context}
        
        YÊU CẦU QUAN TRỌNG:
        1. **Độ chính xác**: Ưu tiên chọn các địa điểm từ "DANH SÁCH ĐỊA ĐIỂM CÓ THẬT" ở trên để đảm bảo tính xác thực.
        2. Nếu danh sách trên không đủ cho lịch trình 1 ngày, bạn có thể gợi ý thêm các địa điểm nổi tiếng khác nhưng PHẢI CHẮC CHẮN nó nằm trong bán kính 5km từ địa chỉ khách sạn.
        3. Sắp xếp lịch trình hợp lý theo thời gian và khoảng cách di chuyển.
        
        NHIỆM VỤ:
        Hãy lập một lịch trình tham quan **1 ngày** (Sáng, Trưa, Chiều, Tối) bắt đầu từ khách sạn này.
        Các địa điểm gợi ý phải **GẦN** khách sạn đó và phù hợp chặt chẽ với Vibe của khách.
        
        YÊU CẦU OUTPUT JSON (Không viết thêm gì ngoài JSON):
        {{
            "morning": {{ "time": "08:00 - 11:00", "activity": "Tên hoạt động/Địa điểm", "desc": "Mô tả ngắn tại sao nơi này hợp vibe", "icon": "fa-coffee" }},
            "noon": {{ "time": "11:30 - 13:00", "activity": "Ăn trưa tại...", "desc": "Mô tả món ăn/không gian", "icon": "fa-utensils" }},
            "afternoon": {{ "time": "14:00 - 17:00", "activity": "...", "desc": "...", "icon": "fa-camera" }},
            "evening": {{ "time": "18:00 - 21:00", "activity": "...", "desc": "...", "icon": "fa-glass-cheers" }}
        }}
        Lưu ý: Icon là class của FontAwesome (ví dụ: fa-coffee, fa-tree). Ngôn ngữ: Tiếng Việt.
        """

        gemini_api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        json_str = clean_json_text(response.text)
        result_json = json.loads(json_str)
        
        # 4. Lưu vào Cache
        db.execute(
            "INSERT OR REPLACE INTO hotel_itineraries (property_token, vibe, itinerary_json) VALUES (?, ?, ?)", 
            (token, vibe, json_str)
        )
        db.commit()
        
        return jsonify(result_json)

    except Exception as e:
        print(f"Trip Genie Error: {e}")
        return jsonify({"error": str(e)}), 500

# --- END ADDITION FOR TRIP GENIE ---

@app.route('/api/mood_search', methods=['POST'])
def mood_search():
    try:
        mood_text = request.form.get('mood_text', '')
        image_file = request.files.get('mood_image')
        
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        client = genai.Client(api_key=gemini_api_key)
        
        inputs = []

        # 1. LẤY THÔNG TIN USER (Nếu đã đăng nhập)
        user_context = "User chưa đăng nhập (Khách vãng lai)."
        if 'user_id' in session:
            db = database.get_db()
            user = db.execute("SELECT preferences FROM users WHERE id=?", (session['user_id'],)).fetchone()
            if user and user['preferences']:
                prefs = json.loads(user['preferences'])
                vibe = prefs.get('vibe', 'Unknown')
                companion = prefs.get('companion', 'Unknown')
                user_context = f"User Preference: Thích kiểu du lịch '{vibe}' (Healing/Adventure/Luxury), thường đi cùng '{companion}'."

        # 2. SUPER PROMPT V2 (Xử lý ảnh chung chung)
        system_prompt = f"""
        Bạn là chuyên gia tư vấn du lịch (Travel Therapist).
        
        THÔNG TIN NGƯỜI DÙNG:
        {user_context}
        
        NHIỆM VỤ: Phân tích hình ảnh + text để tìm 1 thành phố tại Việt Nam.
        
        QUY TẮC SUY LUẬN (ƯU TIÊN TUYỆT ĐỐI):
        
        TRƯỜNG HỢP A: ẢNH ĐẶC TRƯNG (Iconic)
        - Thấy Cầu Vàng/Biển Mỹ Khê -> Đà Nẵng.
        - Thấy Hồ Xuân Hương/Rừng thông -> Đà Lạt.
        - Thấy Ruộng bậc thang/Núi cao -> Sa Pa.
        - Thấy Đèn lồng/Phố cổ -> Hội An.
        - Thấy Biển đảo hoang sơ -> Phú Quốc.

        TRƯỜNG HỢP B: ẢNH CHUNG CHUNG (Generic - Ly cafe, Giường, Mưa, Sách...)
        -> HÃY DÙNG "USER PREFERENCE" ĐỂ QUYẾT ĐỊNH!
        - Ảnh [Mưa/Buồn] + User thích [Healing] -> Gợi ý: "Đà Lạt" hoặc "Huế".
        - Ảnh [Cafe/Sang chảnh] + User thích [Luxury/Business] -> Gợi ý: "TP. Hồ Chí Minh" hoặc "Hà Nội".
        - Ảnh [Thiên nhiên/Cây cối] + User thích [Adventure] -> Gợi ý: "Sa Pa" hoặc "Hà Giang".
        - Ảnh [Hồ bơi/Nắng] + User thích [Family] -> Gợi ý: "Nha Trang" hoặc "Phú Quốc".
        
        *Nếu User chưa có Preference, hãy mặc định: Mưa/Lạnh -> Đà Lạt; Nắng/Biển -> Nha Trang; Phố xá -> TP.HCM.*

        OUTPUT JSON FORMAT ONLY:
        {{
            "city": "Tên thành phố (Chỉ chọn trong list: Hà Nội, TP. Hồ Chí Minh, Đà Nẵng, Nha Trang, Đà Lạt, Sa Pa, Huế, Phú Quốc, Vũng Tàu, Hội An, Cần Thơ, Quy Nhơn)",
            "explanation": "Giải thích ngắn (Tiếng Việt). Nếu ảnh chung chung, hãy nói lái theo sở thích user. Ví dụ: 'Tấm ảnh này tuy đơn giản nhưng mang vibe yên tĩnh, rất hợp với gu Healing của bạn tại Đà Lạt...'",
            "amenities": ["Viết tiếng Anh", "Vd: Spa, Rooftop Bar"],
            "price_range": "Chọn 1: '0-500000', '500000-2000000', '2000000+'"
        }}
        """
        
        inputs.append(system_prompt)
        
        if mood_text:
            inputs.append(f"User Note: {mood_text}")
            
        if image_file:
            img = Image.open(image_file)
            inputs.append(img)
            inputs.append("Analyze this image. If it's iconic, map to location. If generic, map to User Preference.")
        else:
            inputs.append("No image. Analyze user note & preference.")

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=inputs
        )
        
        json_str = clean_json_text(response.text)
        result = json.loads(json_str)
        
        # Fallback an toàn (như cũ)
        valid_cities = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Nha Trang", "Đà Lạt", "Sa Pa", "Huế", "Phú Quốc", "Vũng Tàu", "Hội An", "Cần Thơ", "Quy Nhơn"]
        ai_city = result.get('city', '').strip()
        
        if ai_city not in valid_cities:
             # Logic map fallback đơn giản
            expl = result.get('explanation', '').lower()
            if "biển" in expl: result['city'] = "Nha Trang"
            elif "núi" in expl: result['city'] = "Sa Pa"
            else: result['city'] = "Đà Lạt"
            
        return jsonify(result)

    except Exception as e:
        print(f"Mood Search Error: {e}")
        fallback_result = {
            "city": "Đà Lạt",
            "explanation": "Ảnh của bạn rất nghệ thuật! AI cảm thấy một chút se lạnh và bình yên ở đây, nên Đà Lạt sẽ là lựa chọn tuyệt vời.",
            "amenities": ["Garden", "Fireplace"],
            "price_range": "500000-2000000"
        }
        return jsonify(fallback_result)

# --- END MOOD SEARCH FEATURE ---

    
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            database.init_db()
    app.run(debug=True)







