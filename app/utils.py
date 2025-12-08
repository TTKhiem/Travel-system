import json
import re
from collections import Counter
from typing import Dict, List, Optional

from . import database

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


def clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json|^```|```$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


