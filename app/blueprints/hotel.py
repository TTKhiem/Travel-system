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
from ..utils import analyze_vibe_from_amenities

hotel_bp = Blueprint("hotel", __name__)


@hotel_bp.route("/hotel_results", methods=["POST"])
def api_filter():
    if "user_id" not in session:
        flash("❌ Vui lòng đăng nhập để sử dụng tính năng tìm kiếm!")
        return redirect(url_for("main.home"))

    city = request.form.get("city")
    if not city:
        flash("Hãy chọn địa điểm")
        return redirect(url_for("main.home"))

    price_range = request.form.get("price_range")
    rating_range = request.form.get("rating")
    amenities = request.form.getlist("amenities")
    auto_filled_items = []

    user = None
    if "user_id" in session:
        db = database.get_db()
        user = db.execute(
            "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()

        if user and user["preferences"]:
            try:
                prefs = json.loads(user["preferences"])
                vibe = prefs.get("vibe", "")
                budget = prefs.get("budget", "")
                companion = prefs.get("companion", "")

                if not price_range:
                    if budget == "low":
                        price_range = "0-500000"
                        auto_filled_items.append("price")
                    elif budget == "mid":
                        price_range = "500000-2000000"
                        auto_filled_items.append("price")
                    else:
                        price_range = "2000000+"
                        auto_filled_items.append("price")

                if not rating_range:
                    if vibe == "luxury":
                        rating_range = "4-5"
                        auto_filled_items.append("rating")
                    else:
                        rating_range = "3-5"
                        auto_filled_items.append("rating")

                if not amenities:
                    if vibe == "healing":
                        amenities.append("Pool")
                        auto_filled_items.append("Pool")
                    elif vibe == "adventure":
                        amenities.append("Fitness centre")
                        auto_filled_items.append("Fitness centre")
                    elif companion == "family":
                        amenities.append("Child-friendly")
                        auto_filled_items.append("Child-friendly")
                    elif companion == "couple":
                        amenities.append("Bar")
                        auto_filled_items.append("Bar")
                    else:
                        amenities.append("Free Wi-Fi")
                        auto_filled_items.append("Free Wi-Fi")

            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"Auto-fill Error: {exc}")

    try:
        serp_api_key = os.getenv("SERPAPI_KEY")
        search_api = HotelSearchAPI(serp_api_key)
        search_results = search_api.search_hotels(
            city, price_range, rating_range, amenities
        )

        if search_results and user and user["preferences"]:
            try:
                prefs = json.loads(user["preferences"])
                vibe = prefs.get("vibe", "")
                companion = prefs.get("companion", "")

                for hotel in search_results:
                    score = 0
                    am_list = []
                    raw_ams = hotel.get("amenities", [])
                    for amenity in raw_ams:
                        am_name = amenity if isinstance(amenity, str) else amenity.get("name", "")
                        am_list.append(am_name.lower())
                    am_str = " ".join(am_list)

                    rating = hotel.get("overall_rating", 0)

                    if vibe == "luxury":
                        if rating >= 4.5:
                            score += 50
                        if "pool" in am_str or "spa" in am_str:
                            score += 20
                    elif vibe == "healing":
                        if "spa" in am_str or "garden" in am_str or "pool" in am_str:
                            score += 40
                        if "beach" in am_str or "view" in am_str:
                            score += 20
                    elif vibe == "adventure":
                        if "fitness" in am_str or "gym" in am_str:
                            score += 30
                    elif vibe == "business":
                        if "wi-fi" in am_str or "wifi" in am_str or "desk" in am_str:
                            score += 40
                    hotel["match_score"] = score

                search_results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
                if search_results and search_results[0].get("match_score", 0) > 0:
                    search_results[0]["is_best_match"] = True

            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"Ranking Error: {exc}")

        return render_template(
            "hotel/hotel_results.html",
            hotels=search_results,
            search_params={
                "city": city,
                "price_range": price_range,
                "rating_range": rating_range,
                "amenities": amenities,
            },
            auto_filled_items=auto_filled_items,
        )

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Search Process Error: {exc}")
        return render_template(
            "hotel/hotel_results.html",
            hotels=[],
            error=f"Lỗi: {str(exc)}",
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
        except Exception as exc:  # pragma: no cover - defensive logging
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
        except Exception as exc:  # pragma: no cover - defensive logging
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
        except Exception as exc:  # pragma: no cover - defensive logging
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

        except Exception as exc:  # pragma: no cover - defensive logging
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


