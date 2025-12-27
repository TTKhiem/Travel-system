import json
import os
import re
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .. import database
from ..services.search_service import HotelSearchAPI
from ..utils import analyze_vibe_from_amenities, get_ai_preferences, calculate_match_score, generate_search_hash

hotel_bp = Blueprint("hotel", __name__)

@hotel_bp.route("/search_handler", methods=["POST"])
def api_filter():
    if "user_id" not in session:
        flash("❌ Vui lòng đăng nhập!")
        return redirect(url_for("main.home"))

    city = request.form.get("city")
    if not city:
        flash("Hãy chọn địa điểm")
        return redirect(url_for("main.home"))
    price = request.form.get("price_range", "")
    rating = request.form.get("rating", "")
    amenities = request.form.getlist("amenities")
    ai_autofill_raw = request.form.get("ai_autofill", "off")
    allow_ai_autofill = str(ai_autofill_raw).lower() in ("on", "true", "1", "yes")
            
    db = database.get_db()
    user = None
    if "user_id" in session:
        user = db.execute(
            "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()

        if allow_ai_autofill and user and user["preferences"]:
            try:
                prefs = json.loads(user["preferences"])
                vibe = prefs.get("vibe", "")
                budget = prefs.get("budget", "")
                companion = prefs.get("companion", "")

                ai_suggestion = get_ai_preferences(vibe, companion, budget)
                if not price:
                    price = ai_suggestion["price_range"]
                if not rating:
                    rating = ai_suggestion["rating"]
                if not amenities:
                    amenities = ai_suggestion["amenities"]

            except Exception as exc: 
                print(f"Auto-fill Error: {exc}")

    search_hash = generate_search_hash(city, price, rating, amenities)

    cached = db.execute(
        "SELECT created_at FROM search_cache WHERE search_hash = ?", 
        (search_hash,)
    ).fetchone()
    
    need_fetch = True
    if cached:
        created_at = datetime.strptime(cached["created_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - created_at < timedelta(hours=24):
            need_fetch = False 

    if need_fetch:
        try:
            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)
            results = search_api.search_hotels(city, price, rating, amenities)
            
            if results:
                db.execute(
                    """INSERT OR REPLACE INTO search_cache 
                       (search_hash, city, params_json, results_json, created_at) 
                       VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (
                        search_hash, 
                        city,
                        json.dumps({"city": city, "price": price, "rating": rating, "amenities": amenities}),
                        json.dumps(results, ensure_ascii=False)
                    )
                )
                db.commit()
        except Exception as e:
            print(f"Error fetching new data: {e}")
            flash("Có lỗi khi tìm kiếm, vui lòng thử lại.")
            return redirect(url_for("main.home"))

    return redirect(url_for("hotel.display_results", search_hash=search_hash))

@hotel_bp.route("/results/<search_hash>", methods=["GET"])
def display_results(search_hash):
    db = database.get_db()
    row = db.execute(
        "SELECT results_json, params_json FROM search_cache WHERE search_hash = ?", 
        (search_hash,)
    ).fetchone()

    if not row:
        flash("Kết quả tìm kiếm đã hết hạn hoặc không tồn tại.")
        return redirect(url_for("main.home"))

    try:
        hotels = json.loads(row["results_json"])
        search_params = json.loads(row["params_json"]) 
    except:
        hotels = []
        search_params = {}

    user = None
    if "user_id" in session:
        user = db.execute("SELECT preferences FROM users WHERE id=?", (session["user_id"],)).fetchone()

    if hotels and user and user["preferences"]:
        try:
            prefs = json.loads(user["preferences"])
            for hotel in hotels:
                match_result = calculate_match_score(prefs, hotel)
                hotel["match_score"] = match_result.get("score", 0)
            hotels.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            
            if hotels and hotels[0].get("match_score", 0) > 0:
                hotels[0]["is_best_match"] = True
        except Exception as e:
            print(f"Ranking error: {e}")

    favorite_tokens = []
    if "user_id" in session:
        fav_rows = db.execute(
            "SELECT property_token FROM favorite_places WHERE user_id=?", 
            (session["user_id"],)
        ).fetchall()
        favorite_tokens = [row["property_token"] for row in fav_rows]

    return render_template(
        "hotel/hotel_results.html",
        hotels=hotels,
        favorite_tokens=favorite_tokens,
        search_params={
            "city": search_params.get("city"),
            "price_range": search_params.get("price"),
            "rating_range": search_params.get("rating"),
            "amenities": search_params.get("amenities")
        }
    )

@hotel_bp.route("/hotel/<property_token>")
def hotel_detail(property_token):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    db = database.get_db()
    cached_row = db.execute(
        "SELECT data, created_at FROM hotel_cache WHERE token = ?", (property_token,)
    ).fetchone()
    hotel_data = None
    use_cache = False

    if cached_row:
        stored_time = datetime.strptime(
            cached_row["created_at"], "%Y-%m-%d %H:%M:%S"
        )
        if datetime.now() - stored_time < timedelta(days=5):
            print(f"Cached DB: {property_token}")
            hotel_data = json.loads(cached_row["data"])
            use_cache = True

    if not use_cache:
        print(f"Fetching fresh data from API: {property_token}")
        try:
            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)
            hotel_data = search_api.get_hotel_details(property_token)

            if hotel_data:
                hotel_data["property_token"] = property_token
                json_string = json.dumps(hotel_data, ensure_ascii=False)
                db.execute(
                    "INSERT OR REPLACE INTO hotel_cache (token, data) VALUES (?, ?)",
                    (property_token, json_string),
                )
                db.commit()
        except Exception as exc:
            print(f"Error fetching details: {exc}")
            if cached_row:
                hotel_data = json.loads(cached_row["data"])
            else:
                return render_template(
                    "hotel/hotel_detail.html", error="Không thể tải dữ liệu khách sạn."
                )

    if hotel_data:
        try:
            preview_info = {
                "name": hotel_data.get("name"),
                "image": hotel_data.get("images")[0].get("original_image")
                if hotel_data.get("images")
                else "",
                "price": hotel_data.get("rate_per_night", {}).get("lowest", "Liên hệ"),
                "address": hotel_data.get("address"),
            }
            preview_json = json.dumps(preview_info, ensure_ascii=False)

            check_exist = db.execute(
                "SELECT 1 FROM recently_viewed WHERE user_id=? AND property_token=?",
                (session["user_id"], property_token),
            ).fetchone()

            if check_exist:
                db.execute(
                    "UPDATE recently_viewed SET visited_at = CURRENT_TIMESTAMP, preview_data = ? WHERE user_id = ? AND property_token = ?",
                    (preview_json, session["user_id"], property_token),
                )
            else:
                db.execute(
                    "INSERT INTO recently_viewed (user_id, property_token, preview_data, visited_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                    (session["user_id"], property_token, preview_json),
                )
            db.commit()
        except Exception as exc: 
            print(f"Lỗi lưu lịch sử: {exc}")

    if not hotel_data:
        return render_template("hotel/hotel_detail.html", error="Không tìm thấy khách sạn.")

    match_reason = None
    if "user_id" in session:
        user = db.execute(
            "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()
        recent_entry = db.execute(
            "SELECT match_reason FROM recently_viewed WHERE user_id=? AND property_token=?",
            (session["user_id"], property_token),
        ).fetchone()

        if recent_entry and recent_entry["match_reason"]:
            match_reason = recent_entry["match_reason"]

    if "user_id" in session:
        user_db = db.execute(
            "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()
        current_prefs = (
            json.loads(user_db["preferences"]) if user_db and user_db["preferences"] else {}
        )

        try:
            price_str = hotel_data.get("rate_per_night", {}).get("lowest", "0")
            price_num = int(re.sub(r"[^\d]", "", str(price_str)))

            if price_num > 1800000:
                session["expensive_view_count"] = session.get("expensive_view_count", 0) + 1
                if session["expensive_view_count"] >= 3:
                    if current_prefs.get("budget") != "high":
                        current_prefs["budget"] = "high"
                        db.execute(
                            "UPDATE users SET preferences = ? WHERE id = ?",
                            (json.dumps(current_prefs), session["user_id"]),
                        )
                        db.commit()
                        print("✨ Passive Learning: Đã nâng cấp user lên HIGH budget.")
                        session["expensive_view_count"] = 0
        except Exception as exc:  
            print(f"Budget Learning Error: {exc}")

        try:
            raw_amenities = []
            if hotel_data.get("amenities"):
                for amenity in hotel_data["amenities"]:
                    val = amenity.get("name") if isinstance(amenity, dict) else amenity
                    raw_amenities.append(val)

            detected_vibe = analyze_vibe_from_amenities(raw_amenities)
            if detected_vibe:
                if "vibe_tracker" not in session:
                    session["vibe_tracker"] = {}

                current_score = session["vibe_tracker"].get(detected_vibe, 0) + 1
                session["vibe_tracker"][detected_vibe] = current_score
                session.modified = True
                print(f"👁 User viewing {detected_vibe} hotel. Score: {current_score}")
                if current_score >= 4:
                    if current_prefs.get("vibe") != detected_vibe:
                        current_prefs["vibe"] = detected_vibe
                        db.execute(
                            "UPDATE users SET preferences = ? WHERE id = ?",
                            (json.dumps(current_prefs), session["user_id"]),
                        )
                        db.commit()
                        print(
                            f"✨ Passive Learning: Đã đổi Vibe user sang {detected_vibe.upper()} dựa trên hành vi."
                        )
                        session["vibe_tracker"] = {}

        except Exception as exc:  
            print(f"Vibe Learning Error: {exc}")

    dynamic_price = request.args.get("price")
    if dynamic_price:
        if "rate_per_night" not in hotel_data:
            hotel_data["rate_per_night"] = {}
        hotel_data["rate_per_night"]["lowest"] = dynamic_price
        hotel_data["is_dynamic_price"] = True

    check_in = request.args.get("check_in")
    check_out = request.args.get("check_out")
    if check_in and check_out:
        hotel_data["search_context"] = {"check_in": check_in, "check_out": check_out}

    filter_rating = request.args.get("filter_rating")
    sort_review = request.args.get("sort_review", "newest")

    query = "SELECT * FROM user_reviews WHERE property_token = ?"
    params = [property_token]

    if filter_rating and filter_rating.isdigit():
        query += " AND rating = ?"
        params.append(int(filter_rating))

    if sort_review == "oldest":
        query += " ORDER BY created_at ASC"
    elif sort_review == "highest":
        query += " ORDER BY rating DESC, created_at DESC"
    elif sort_review == "lowest":
        query += " ORDER BY rating ASC, created_at DESC"
    else:
        query += " ORDER BY created_at DESC"

    local_reviews = db.execute(query, tuple(params)).fetchall()

    is_favorite = False
    if "user_id" in session:
        fav_check = db.execute(
            "SELECT 1 FROM favorite_places WHERE user_id=? AND property_token=?",
            (session["user_id"], property_token),
        ).fetchone()
        if fav_check:
            is_favorite = True

    return render_template(
        "hotel/hotel_detail.html",
        match_reason=match_reason,
        hotel=hotel_data,
        local_reviews=local_reviews,
        is_favorite=is_favorite,
    )


@hotel_bp.route("/hotel/review", methods=["POST"])
def add_review():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    property_token = request.form.get("property_token")
    rating = request.form.get("rating")
    comment = request.form.get("comment")
    username = session["username"]

    price = request.form.get("current_price")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")

    if property_token and rating:
        db = database.get_db()
        db.execute(
            "INSERT INTO user_reviews (property_token, username, rating, comment) VALUES (?, ?, ?, ?)",
            (property_token, username, int(rating), comment),
        )
        db.execute(
            "DELETE FROM review_summaries WHERE property_token = ?", (property_token,)
        )
        db.commit()
        flash("✅ Cảm ơn bạn đã đánh giá!")
    else:
        flash("❌ Vui lòng chọn số sao.")

    return redirect(
        url_for(
            "hotel.hotel_detail",
            property_token=property_token,
            price=price,
            check_in=check_in,
            check_out=check_out,
        )
    )


