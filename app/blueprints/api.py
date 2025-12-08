import json
import os
import re
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session
from PIL import Image
from google import genai

from .. import database
from ..services.search_service import HotelSearchAPI
from ..utils import clean_json_text, generate_ai_suggestion, get_user_recent_city

api_bp = Blueprint("api", __name__)


def _get_gemini_client():
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=gemini_api_key)


@api_bp.post("/api/summarize_reviews")
def summarize_reviews():
    try:
        data = request.get_json(force=True)
        property_token = data.get("property_token")
        if not property_token:
            return jsonify({"error": "Missing token"}), 400

        db = database.get_db()
        cached = db.execute(
            "SELECT summary_content, updated_at FROM review_summaries WHERE property_token = ?",
            (property_token,),
        ).fetchone()

        if cached and cached["summary_content"]:
            try:
                last_update = datetime.strptime(
                    cached["updated_at"], "%Y-%m-%d %H:%M:%S"
                )
                if datetime.utcnow() - last_update < timedelta(hours=24):
                    print(f"Using cached summary for {property_token}")
                    return jsonify({"summary": cached["summary_content"]})
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"Date parse error: {exc}")

        reviews = db.execute(
            "SELECT rating, comment FROM user_reviews WHERE property_token = ? AND comment IS NOT NULL ORDER BY created_at DESC LIMIT 20",
            (property_token,),
        ).fetchall()

        if not reviews:
            return jsonify({"summary": None})

        reviews_text = "\n".join(
            [f"- {r['rating']} sao: {r['comment']}" for r in reviews if r["comment"].strip()]
        )

        if not reviews_text:
            return jsonify({"summary": None})

        prompt = (
            "Dưới đây là các đánh giá của khách hàng về một khách sạn:\n"
            f"{reviews_text}\n\n"
            "Yêu cầu: Hãy viết một đoạn tóm tắt ngắn gọn (khoảng 3-4 câu) bằng tiếng Việt "
            "về ưu điểm và nhược điểm chính của khách sạn này dựa trên các đánh giá trên."
        )

        client = _get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        new_summary = response.text
        db.execute(
            "INSERT OR REPLACE INTO review_summaries (property_token, summary_content, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (property_token, new_summary),
        )
        db.commit()

        return jsonify({"summary": new_summary})

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Summary Error: {exc}")
        return jsonify({"error": str(exc)}), 500


@api_bp.post("/api/hotel_chat")
def hotel_chat():
    try:
        payload = request.get_json(force=True) or {}
        user_message = (payload.get("message") or "").strip()
        property_token = payload.get("property_token")
        dynamic_context = payload.get("dynamic_context") or {}
        hotel_fallback = payload.get("hotel_fallback") or {}

        if not user_message:
            return jsonify({"error": "message is required"}), 400

        client = _get_gemini_client()

        hotel_data = {}
        if property_token:
            db = database.get_db()
            row = db.execute(
                "SELECT data FROM hotel_cache WHERE token = ?", (property_token,)
            ).fetchone()
            if row:
                hotel_data = json.loads(row["data"])
            else:
                hotel_data = hotel_fallback
        else:
            hotel_data = hotel_fallback

        user_prefs_context = ""
        if "user_id" in session:
            db = database.get_db()
            user = db.execute(
                "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
            ).fetchone()
            if user and user["preferences"]:
                prefs = json.loads(user["preferences"])
                vibe_map = {
                    "healing": "🌿 Chữa lành (yên tĩnh, spa)",
                    "adventure": "🎒 Khám phá (hoạt động ngoài trời)",
                    "luxury": "💎 Sang chảnh (5 sao)",
                    "business": "💼 Công tác",
                }
                user_prefs_context = f"""
                THÔNG TIN SỞ THÍCH CỦA USER:
                - Phong cách: {vibe_map.get(prefs.get('vibe'), prefs.get('vibe', 'N/A'))}
                - Đi cùng: {prefs.get('companion', 'N/A')}
                - Ngân sách: {prefs.get('budget', 'N/A')}
                
                LƯU Ý: Khi tư vấn, hãy nhấn mạnh các điểm phù hợp với sở thích của user.
                Ví dụ: Nếu user thích "healing" và khách sạn có Spa -> nhấn mạnh Spa.
                """

        current_price = dynamic_context.get("price", "N/A")
        check_in = dynamic_context.get("check_in", "N/A")
        check_out = dynamic_context.get("check_out", "N/A")
        hotel_data_str = json.dumps(hotel_data, indent=2, ensure_ascii=False)

        system_instruction = (
            "You are a helpful AI assistant for hotel booking. Answer user questions based on this hotel data:\n"
            f"Price: {current_price} (Dates: {check_in}-{check_out}).\n"
            f"{hotel_data_str}\n"
            f"{user_prefs_context}"
            "Reply in Vietnamese, friendly and personalized based on user preferences if available."
        )
        prompt = f"{system_instruction}\n\nUser: {user_message}"

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        reply_text = response.text if response.text else "Xin lỗi, AI đang bận."

        return jsonify({"reply": reply_text})

    except Exception as exc:  # pragma: no cover - defensive logging
        return jsonify({"error": str(exc)}), 500


@api_bp.post("/api/compare_ai")
def compare_ai_analysis():
    try:
        data = request.get_json()
        hotels = data.get("hotels", [])
        if len(hotels) < 2:
            return jsonify({"reply": "Cần ít nhất 2 khách sạn để so sánh."})

        prompt_content = "So sánh ngắn gọn các khách sạn sau:\n"
        for hotel in hotels:
            prompt_content += (
                f"- {hotel['name']}: Giá {hotel.get('rate_per_night', {}).get('lowest', 'N/A')}, "
                f"Rating {hotel.get('overall_rating', 'N/A')}.\n"
            )

        client = _get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_content + "\nTrả lời bằng tiếng Việt, ngắn gọn.",
        )
        return jsonify({"reply": response.text})

    except Exception as exc:  # pragma: no cover - defensive logging
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/get_chat_history", methods=["GET"])
def get_chat_history():
    if "chat_history" not in session:
        session["chat_history"] = []
    return jsonify(session["chat_history"])


@api_bp.route("/api/clear_chat", methods=["POST"])
def clear_chat():
    session.pop("chat_history", None)
    return jsonify({"status": "cleared"})


@api_bp.route("/api/chat_search", methods=["POST"])
def api_chat_search():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    page_context = data.get("page_context", {})

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    if "chat_history" not in session:
        session["chat_history"] = []

    history = session["chat_history"]

    recent_history = history[-6:]
    history_text = ""
    for msg in recent_history:
        role = "User" if msg["role"] == "user" else "AI"
        content = msg["content"]
        if msg.get("type") == "search_result":
            content = "[Đã hiển thị danh sách khách sạn]"
        history_text += f"{role}: {content}\n"

    user_prefs = None
    if "user_id" in session:
        db = database.get_db()
        user = db.execute(
            "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()
        if user and user["preferences"]:
            user_prefs = json.loads(user["preferences"])

    current_view_context = ""
    if page_context and page_context.get("hotels"):
        hotel_list_str = "\n".join(
            [
                f"- {hotel['name']}:\n   + Giá: {hotel['price']}\n   + Đánh giá: {hotel['rating']}/5\n   + Tiện nghi: {hotel.get('amenities', 'Không rõ')}"
                for hotel in page_context["hotels"]
            ]
        )
        current_view_context = f"""
        THÔNG TIN TRANG HIỆN TẠI NGƯỜI DÙNG ĐANG XEM:
        Người dùng đang đứng ở trang kết quả tìm kiếm. Dưới đây là danh sách các khách sạn đang hiển thị trên màn hình:
        {hotel_list_str}
        
        NHIỆM VỤ:
        1. So sánh: Nếu user hỏi "cái nào có hồ bơi", "cái nào tiện nghi nhất", hãy DÙNG DỮ LIỆU "Tiện nghi" ở trên để trả lời chính xác.
        2. Tư vấn giá: Dùng dữ liệu "Giá" để so sánh đắt/rẻ.
        3. Tuyệt đối không bịa đặt tiện nghi nếu trong danh sách không ghi (hãy nói là "thông tin chưa đề cập").
        """

    prefs_context = ""
    if user_prefs:
        vibe_map = {
            "healing": "🌿 Chữa lành (yên tĩnh, spa, thiên nhiên)",
            "adventure": "🎒 Khám phá (hoạt động ngoài trời, thể thao)",
            "luxury": "💎 Sang chảnh (5 sao, dịch vụ cao cấp)",
            "business": "💼 Công tác (Wi-Fi tốt, vị trí trung tâm)",
        }
        companion_map = {
            "solo": "Một mình",
            "couple": "Cặp đôi",
            "family": "Gia đình",
            "friends": "Nhóm bạn",
        }
        budget_map = {
            "low": "< 500k/đêm",
            "mid": "500k - 2tr/đêm",
            "high": "> 2tr/đêm",
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

    client = _get_gemini_client()

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
            model="gemini-2.5-flash",
            contents=prompt,
        )

        json_str = response.text.strip()
        json_str = re.sub(r"^```json|^```|```$", "", json_str, flags=re.MULTILINE).strip()

        parsed = json.loads(json_str)

        history.append({"role": "user", "content": user_msg})

        if parsed.get("type") == "search":
            city = parsed.get("city")

            if not city:
                for old_msg in reversed(history):
                    if old_msg.get("search_params", {}).get("city"):
                        city = old_msg["search_params"]["city"]
                        break

            if not city:
                reply = "Bạn muốn tìm khách sạn ở thành phố nào nhỉ?"
                history.append({"role": "ai", "content": reply, "type": "chat"})
                session.modified = True
                return jsonify({"type": "chat", "reply_text": reply})

            price_range = parsed.get("price_range")
            rating = parsed.get("rating")
            amenities = parsed.get("amenities") or []

            if user_prefs:
                if not price_range:
                    budget = user_prefs.get("budget")
                    if budget == "low":
                        price_range = "0-500000"
                    elif budget == "mid":
                        price_range = "1000000-2000000"
                    elif budget == "high":
                        price_range = "2000000+"

                if not rating:
                    vibe = user_prefs.get("vibe")
                    if vibe == "luxury":
                        rating = "4-5"

                if len(amenities) == 0:
                    vibe = user_prefs.get("vibe")
                    companion = user_prefs.get("companion")

                    if vibe == "healing":
                        amenities.extend(["Pool"])
                    elif vibe == "adventure":
                        amenities.extend(["Fitness centre", "Pool"])
                    elif vibe == "luxury":
                        amenities.extend(["Pool", "Fitness centre"])

                    if companion == "family":
                        if "Child-friendly" not in amenities:
                            amenities.append("Child-friendly")
                        if "Pool" not in amenities:
                            amenities.append("Pool")
                    elif companion == "couple":
                        if "Pool" not in amenities:
                            amenities.append("Pool")

            serp_api_key = os.getenv("SERPAPI_KEY")
            search_api = HotelSearchAPI(serp_api_key)

            hotels = search_api.search_hotels(
                city,
                price_range,
                rating,
                amenities if len(amenities) > 0 else None,
            )

            hotels_lite = []
            if hotels:
                for hotel in hotels[:4]:
                    hotels_lite.append(
                        {
                            "name": hotel.get("name"),
                            "property_token": hotel.get("property_token"),
                            "rate_per_night": hotel.get("rate_per_night"),
                            "overall_rating": hotel.get("overall_rating"),
                            "images": [{"original_image": hotel["images"][0]["original_image"]}]
                            if hotel.get("images")
                            else [],
                        }
                    )

            reply_text = parsed.get("reply_text", f"Kết quả tìm kiếm tại {city}:")

            history.append(
                {
                    "role": "ai",
                    "content": reply_text,
                    "type": "search_result",
                    "search_params": {
                        "city": city,
                        "price_range": parsed.get("price_range"),
                        "amenities": parsed.get("amenities"),
                    },
                    "hotels": hotels_lite,
                }
            )
            session.modified = True

            return jsonify(
                {
                    "type": "search_result",
                    "reply_text": reply_text,
                    "hotels": hotels,
                }
            )

        reply_text = parsed.get("reply_text")
        history.append({"role": "ai", "content": reply_text, "type": "chat"})
        session.modified = True

        return jsonify({"type": "chat", "reply_text": reply_text})

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Chat Error: {exc}")
        return jsonify(
            {
                "type": "chat",
                "reply_text": "Xin lỗi, server đang bận xíu. Bạn thử lại sau nhé!",
            }
        )


@api_bp.route("/api/update_preferences", methods=["POST"])
def update_preferences():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        prefs_json = json.dumps(data)

        db = database.get_db()
        db.execute(
            "UPDATE users SET preferences = ? WHERE id = ?",
            (prefs_json, session["user_id"]),
        )
        db.commit()

        return jsonify({"message": "Success"}), 200

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Update Prefs Error: {exc}")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/get_match_reason", methods=["POST"])
def get_match_reason_api():
    if "user_id" not in session:
        return jsonify({"match": None})

    data = request.get_json()
    property_token = data.get("property_token")
    hotel_name = data.get("hotel_name")
    amenities = data.get("amenities", [])

    db = database.get_db()

    recent = db.execute(
        "SELECT match_reason FROM recently_viewed WHERE user_id=? AND property_token=?",
        (session["user_id"], property_token),
    ).fetchone()

    if recent and recent["match_reason"]:
        return jsonify({"match": recent["match_reason"]})

    user = db.execute(
        "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()
    if user and user["preferences"]:
        prefs = json.loads(user["preferences"])

        prompt = f"""
        User Prefer: {json.dumps(prefs)}. 
        Hotel: {hotel_name}, Amenities: {str(amenities[:10])}.
        Task: 
        1. Calculate match score (0-100%).
        2. Write ONE short sentence explaining WHY in Vietnamese.
        Format: "Score|Sentence"
        """
        try:
            client = _get_gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            match_reason = response.text.strip()

            db.execute(
                "UPDATE recently_viewed SET match_reason = ? WHERE user_id=? AND property_token=?",
                (match_reason, session["user_id"], property_token),
            )
            db.commit()

            return jsonify({"match": match_reason})
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Match API Error: {exc}")
            return jsonify({"match": None})

    return jsonify({"match": None})


@api_bp.route("/api/get_home_suggestion", methods=["GET"])
def get_home_suggestion_api():
    if "user_id" not in session:
        return jsonify({"suggestion": None, "is_logged_in": False})

    db = database.get_db()
    user = db.execute(
        "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()

    suggestion = None
    if user and user["preferences"]:
        try:
            prefs = json.loads(user["preferences"])
            recent_city = get_user_recent_city(session["user_id"])
            suggestion = generate_ai_suggestion(prefs, history_city=recent_city)

        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Error generating suggestion: {exc}")
            suggestion = generate_ai_suggestion(prefs)

    return jsonify({"suggestion": suggestion, "is_logged_in": True})


@api_bp.route("/api/generate_itinerary", methods=["POST"])
def generate_itinerary():
    try:
        data = request.get_json()
        token = data.get("property_token")
        hotel_name = data.get("hotel_name")
        address = data.get("address")

        vibe = "adventure"
        if "user_id" in session:
            db = database.get_db()
            user = db.execute(
                "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
            ).fetchone()
            if user and user["preferences"]:
                prefs = json.loads(user["preferences"])
                vibe = prefs.get("vibe", "adventure")

        db = database.get_db()
        cached = db.execute(
            "SELECT itinerary_json FROM hotel_itineraries WHERE property_token=? AND vibe=?",
            (token, vibe),
        ).fetchone()

        if cached:
            print(f"🎯 Trip Genie: Hit Cache for {token} - {vibe}")
            return jsonify(json.loads(cached["itinerary_json"]))

        hotel_cache_row = db.execute(
            "SELECT data FROM hotel_cache WHERE token = ?", (token,)
        ).fetchone()

        real_places_context = ""
        if hotel_cache_row:
            hotel_data = json.loads(hotel_cache_row["data"])
            nearby_list = hotel_data.get("nearby_places", [])

            if nearby_list:
                places_str = "\n".join(
                    [
                        f"- {place['name']} ({place.get('transportations', [{'duration': 'Gần'}])[0]['duration']})"
                        for place in nearby_list[:15]
                    ]
                )
                real_places_context = f"""
                DANH SÁCH ĐỊA ĐIỂM CÓ THẬT XUNG QUANH KHÁCH SẠN (Ưu tiên tuyệt đối sử dụng các địa điểm này):
                {places_str}
                """

        print(f"🤖 Trip Genie: Calling AI for {token} - {vibe}")

        vibe_desc = {
            "healing": "thư giãn, yên tĩnh, spa, thiên nhiên, không xô bồ",
            "adventure": "khám phá, vận động, trải nghiệm địa phương độc lạ",
            "luxury": "sang trọng, check-in đẳng cấp, fine dining, dịch vụ 5 sao",
            "business": "tiện lợi, cafe làm việc, thư giãn nhẹ nhàng buổi tối",
        }
        user_vibe_detail = vibe_desc.get(vibe, "cân bằng")

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

        client = _get_gemini_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        json_str = clean_json_text(response.text)
        result_json = json.loads(json_str)

        db.execute(
            "INSERT OR REPLACE INTO hotel_itineraries (property_token, vibe, itinerary_json) VALUES (?, ?, ?)",
            (token, vibe, json_str),
        )
        db.commit()

        return jsonify(result_json)

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Trip Genie Error: {exc}")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/mood_search", methods=["POST"])
def mood_search():
    try:
        mood_text = request.form.get("mood_text", "")
        image_file = request.files.get("mood_image")

        client = _get_gemini_client()

        inputs = []

        user_context = "User chưa đăng nhập (Khách vãng lai)."
        if "user_id" in session:
            db = database.get_db()
            user = db.execute(
                "SELECT preferences FROM users WHERE id=?", (session["user_id"],)
            ).fetchone()
            if user and user["preferences"]:
                prefs = json.loads(user["preferences"])
                vibe = prefs.get("vibe", "Unknown")
                companion = prefs.get("companion", "Unknown")
                user_context = (
                    f"User Preference: Thích kiểu du lịch '{vibe}' (Healing/Adventure/Luxury), "
                    f"thường đi cùng '{companion}'."
                )

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
            inputs.append(
                "Analyze this image. If it's iconic, map to location. If generic, map to User Preference."
            )
        else:
            inputs.append("No image. Analyze user note & preference.")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=inputs,
        )

        json_str = clean_json_text(response.text)
        result = json.loads(json_str)

        valid_cities = [
            "Hà Nội",
            "TP. Hồ Chí Minh",
            "Đà Nẵng",
            "Nha Trang",
            "Đà Lạt",
            "Sa Pa",
            "Huế",
            "Phú Quốc",
            "Vũng Tàu",
            "Hội An",
            "Cần Thơ",
            "Quy Nhơn",
        ]
        ai_city = result.get("city", "").strip()

        if ai_city not in valid_cities:
            expl = result.get("explanation", "").lower()
            if "biển" in expl:
                result["city"] = "Nha Trang"
            elif "núi" in expl:
                result["city"] = "Sa Pa"
            else:
                result["city"] = "Đà Lạt"

        return jsonify(result)

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Mood Search Error: {exc}")
        fallback_result = {
            "city": "Đà Lạt",
            "explanation": "Ảnh của bạn rất nghệ thuật! AI cảm thấy một chút se lạnh và bình yên ở đây, nên Đà Lạt sẽ là lựa chọn tuyệt vời.",
            "amenities": ["Garden", "Fireplace"],
            "price_range": "500000-2000000",
        }
        return jsonify(fallback_result)


