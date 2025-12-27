import json
import re
import hashlib
from collections import Counter
from typing import Dict, List, Optional

from . import database

def generate_search_hash(city, price, rating, amenities):
    c_clean = str(city).strip().lower() if city else ""
    p_clean = str(price).strip().lower() if price else ""
    r_clean = str(rating).strip().lower() if rating else ""
    
    if amenities:
        a_clean = ",".join(sorted([str(a).strip().lower() for a in amenities if a]))
    else:
        a_clean = ""

    raw_string = f"{c_clean}|{p_clean}|{r_clean}|{a_clean}"
    
    return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

def get_user_recent_city(user_id: int) -> Optional[str]:
    db = database.get_db()
    rows = db.execute(
        """
        SELECT preview_data
        FROM recently_viewed
        WHERE user_id = ?
        ORDER BY visited_at DESC
        LIMIT 10
        """,
        (user_id,),
    ).fetchall()

    if not rows:
        return None

    city_mapping = {
        "hà nội": "Hà Nội",
        "hanoi": "Hà Nội",
        "ha noi": "Hà Nội",
        "đà nẵng": "Đà Nẵng",
        "da nang": "Đà Nẵng",
        "hồ chí minh": "TP. Hồ Chí Minh",
        "ho chi minh": "TP. Hồ Chí Minh",
        "sai gon": "TP. Hồ Chí Minh",
        "đà lạt": "Đà Lạt",
        "da lat": "Đà Lạt",
        "nha trang": "Nha Trang",
        "huế": "Huế",
        "hue": "Huế",
        "sa pa": "Sa Pa",
        "sapa": "Sa Pa",
        "phú quốc": "Phú Quốc",
        "phu quoc": "Phú Quốc",
        "vũng tàu": "Vũng Tàu",
        "vung tau": "Vũng Tàu",
    }

    cities_found: List[str] = []
    for row in rows:
        try:
            data = json.loads(row["preview_data"])
            address = data.get("address", "").lower()
            for key, val in city_mapping.items():
                if key in address:
                    cities_found.append(val)
                    break
        except Exception:
            continue

    if not cities_found:
        return None

    most_common = Counter(cities_found).most_common(1)
    return most_common[0][0] if most_common else None


def analyze_vibe_from_amenities(amenities_list: List[str]) -> Optional[str]:
    vibe_keywords: Dict[str, List[str]] = {
        "healing": [
            "spa",
            "massage",
            "yoga",
            "garden",
            "meditation",
            "sauna",
            "steam room",
            "hot tub",
        ],
        "adventure": [
            "fitness",
            "gym",
            "hiking",
            "diving",
            "bike",
            "canoe",
            "windsurfing",
        ],
        "luxury": [
            "butler",
            "limousine",
            "infinity pool",
            "wine",
            "champagne",
            "club",
        ],
        "business": ["meeting", "conference", "business centre", "printer", "fax"],
    }

    am_text = " ".join([str(a).lower() for a in amenities_list])
    scores = {k: 0 for k in vibe_keywords}

    for vibe, keywords in vibe_keywords.items():
        for kw in keywords:
            if kw in am_text:
                scores[vibe] += 1

    best_vibe = max(scores, key=scores.get)
    if scores[best_vibe] >= 2:
        return best_vibe
    return None


def generate_ai_suggestion(user_prefs: Dict, history_city: Optional[str] = None) -> Optional[Dict]:
    if not user_prefs:
        return None

    vibe = user_prefs.get("vibe", "adventure")
    budget = user_prefs.get("budget", "mid")

    vibe_config = {
        "healing": {
            "icon": "🌿",
            "greetings": [
                "Không gian yên tĩnh để chữa lành tâm hồn",
                "Tìm về thiên nhiên, bỏ lại âu lo",
                "Nghỉ dưỡng thư thái, tái tạo năng lượng",
            ],
        },
        "adventure": {
            "icon": "🎒",
            "greetings": [
                "Sẵn sàng cho chuyến khám phá tiếp theo chưa?",
                "Những trải nghiệm mới đang chờ đón bạn",
                "Xách balo lên và đi thôi!",
            ],
        },
        "luxury": {
            "icon": "💎",
            "greetings": [
                "Trải nghiệm đẳng cấp thượng lưu",
                "Kỳ nghỉ sang trọng xứng tầm với bạn",
                "Tận hưởng dịch vụ 5 sao hoàn hảo",
            ],
        },
        "business": {
            "icon": "💼",
            "greetings": [
                "Tiện nghi tối ưu cho chuyến công tác",
                "Kết nối thành công, nghỉ ngơi trọn vẹn",
                "Không gian làm việc chuyên nghiệp",
            ],
        },
    }

    fallback_cities = {
        "healing": ["Đà Lạt", "Sa Pa", "Huế"],
        "adventure": ["Đà Nẵng", "Nha Trang", "Sa Pa"],
        "luxury": ["Phú Quốc", "Đà Nẵng", "TP. Hồ Chí Minh"],
        "business": ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng"],
    }

    import random

    config = vibe_config.get(vibe, vibe_config["adventure"])
    if history_city:
        city = history_city
        greeting = f"Tiếp tục kế hoạch vi vu tại {city} nhé?"
    else:
        city = random.choice(fallback_cities.get(vibe, fallback_cities["adventure"]))
        greeting = random.choice(config["greetings"])

    budget_map = {
        "low": "0-500000",
        "mid": "1000000-2000000",
        "high": "2000000+",
    }
    price_range = budget_map.get(budget, "1000000-2000000")

    return {
        "city": city,
        "price_range": price_range,
        "vibe_icon": config["icon"],
        "greeting": greeting,
    }

def get_ai_preferences(vibe, companion, budget):
    profiles = {
        "luxury": {
            "rating": "4-5",
            "amenities": ["Pool", "Spa", "Bar", "Air-conditioned"],
            "price_factor": "high"
        },
        "healing": {
            "rating": "3-5", 
            "amenities": ["Pool", "Spa", "Air-conditioned"],
            "price_factor": "mid"
        },
        "adventure": {
            "rating": "3-5",
            "amenities": ["Fitness centre", "Free Wi-Fi", "Air-conditioned"],
            "price_factor": "low"
        },
        "business": {
            "rating": "3-5",
            "amenities": ["Free Wi-Fi", "Room service", "Air-conditioned"],
            "price_factor": "mid"
        },
        "family": {
            "rating": "3-5",
            "amenities": ["Child-friendly", "Pool", "Restaurant", "Air-conditioned"],
            "price_factor": "mid"
        },
        "couple": {
            "rating": "4-5",
            "amenities": ["Spa", "Bar", "Air-conditioned"],
            "price_factor": "mid"
        }
    }

    budget_map = {
        "low": "0-500000",
        "mid": "500000-2000000",
        "high": "2000000+",
    }

    suggestion = {
        "rating": "3-5",
        "amenities": ["Free Wi-Fi"],
        "price_range": budget_map.get(budget, "500000-2000000")
    }

    if vibe in profiles:
        prof = profiles[vibe]
        suggestion["rating"] = prof["rating"]
        suggestion["amenities"].extend(prof["amenities"])
        
        if not budget: 
            p_factor = prof["price_factor"]
            suggestion["price_range"] = budget_map.get(p_factor, "500000-2000000")

    if companion == "family":
        suggestion["amenities"].extend(profiles["family"]["amenities"])
    elif companion == "couple":
        suggestion["amenities"].extend(profiles["couple"]["amenities"])

    suggestion["amenities"] = list(set(suggestion["amenities"]))
    return suggestion

def calculate_match_score(user_prefs: Dict, hotel_data: Dict) -> Dict:
    if not user_prefs or not hotel_data:
        return {"score": 0, "reason": "Chưa đủ dữ liệu để đánh giá."}

    user_vibe = user_prefs.get("vibe", "adventure")
    user_budget = user_prefs.get("budget", "mid")
    user_companion = user_prefs.get("companion", "solo")
    
    amenities = []
    raw_amenities = hotel_data.get("amenities", [])
    for a in raw_amenities:
        if isinstance(a, dict): amenities.append(a.get("name", "").lower())
        else: amenities.append(str(a).lower())
    amenities_text = " ".join(amenities)

    price_str = str(hotel_data.get("rate_per_night", {}).get("lowest", "0"))
    price = int(re.sub(r"[^\d]", "", price_str)) if price_str else 0
    rating = float(hotel_data.get("overall_rating", 0) or 0)

    score = 0
    reasons = []

    vibe_mapping = {
        "healing": ["spa", "indoor pool", "outdoor pool", "pool", "beach access", "air conditioning"],
        "adventure": ["fitness center", "outdoor pool", "beach access", "pool", "indoor pool", "outdoor pool"],
        "luxury": ["spa", "bar", "room service", "restaurant", "pool", "indoor pool", "outdoor pool"],
        "business": ["free wi-fi", "parking", "free parking", "air conditioning", "restaurant"]
    }

    vibe_mapping_vi = {
        "healing": ["spa", "bể bơi trong nhà", "bể bơi ngoài trời", "bể bơi", "có biển", "điều hòa nhiệt độ"],
        "adventure": ["trung tâm thể dục", "bể bơi ngoài trời", "có biển", "bể bơi", "bể bơi trong nhà", "bể bơi ngoài trời"],
        "luxury": ["spa", "bar", "dịch vụ phòng", "nhà hàng", "bể bơi", "bể bơi trong nhà", "bể bơi ngoài trời"],
        "business": ["wi-fi miễn phí", "đỗ xe", "đỗ xe miễn phí", "điều hòa nhiệt độ", "nhà hàng"]
    }
    
    target_kws = vibe_mapping.get(user_vibe, [])
    target_kws = vibe_mapping_vi.get(user_vibe, [])
    found_kws = []
    for kw in target_kws:
        if kw in amenities_text:
            found_kws.append(kw)
    
    if found_kws:
        score += min(len(found_kws) * 10, 40)
        kw_display = ", ".join([k.title() for k in found_kws[:2]])
        reasons.append(f"Có tiện nghi {kw_display} hợp gu {user_vibe.capitalize()}")
    else:
        if "free breakfast" in amenities_text:
            score += 5
            reasons.append("Có miễn phí bữa sáng")

    budget_ranges = {
        "low": (0, 800000),
        "mid": (800000, 2500000),
        "high": (2500000, 99999999)
    }
    min_b, max_b = budget_ranges.get(user_budget, (0, 99999999))
    
    if min_b <= price <= max_b:
        score += 30
        reasons.append("Giá phù hợp ngân sách")
    elif user_budget == "low" and price > max_b:
        score -= 10 
        reasons.append("Giá hơi cao so với ngân sách")
    elif user_budget == "high" and price < 1000000:
        score += 10 
        reasons.append("Giá tiết kiệm hơn dự kiến")

    companion_mapping = {
        "family": ["child-friendly", "free breakfast", "pool"],
        "couple": ["spa", "bar", "room service", "restaurant"],
        "business": ["free wi-fi", "fitness center", "free parking"],
        "solo": ["free wi-fi", "bar"]
    }
    companion_mapping_vi = {
        "family": ["phù hợp với trẻ em", "bữa sáng miễn phí", "bể bơi"],
        "couple": ["spa", "bar", "dịch vụ phòng", "nhà hàng"],
        "business": ["wi-fi miễn phí", "trung tâm thể dục", "đỗ xe miễn phí"],
        "solo": ["wi-fi miễn phí", "bar"]
    }
    comp_kws = companion_mapping.get(user_companion, [])
    comp_kws = companion_mapping_vi.get(user_companion, [])
    found_comp = []
    for kw in comp_kws:
        if kw in amenities_text:
            found_comp.append(kw)
    
    if found_comp:
        score += 20
        reasons.append(f"Tiện nghi phù hợp cho {user_companion.capitalize()}")

    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 5
    
    score = max(0, min(100, score))

    final_reason = ""
    if score >= 80:
        main_point = reasons[0] if reasons else "Rất đáng trải nghiệm"
        final_reason = f"Tuyệt vời ({score}%)! {main_point}."
    elif score >= 50:
        main_point = reasons[0] if reasons else "Khá ổn"
        final_reason = f"Phù hợp ({score}%). {main_point}."
    else:
        final_reason = f"Chưa thực sự khớp ({score}%). {reasons[-1] if reasons else 'Thiếu tiện nghi mong muốn'}."

    return {"score": score, "reason": final_reason}


def clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json|^```|```$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


