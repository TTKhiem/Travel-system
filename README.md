# Accomodation Project (Computational Thinking)
## 📋 Mục Lục

- [Tính Năng Nổi Bật](#-tính-năng-nổi-bật)
- [Hướng Dẫn Sử Dụng](#-hướng-dẫn-sử-dụng)
- [Cấu Trúc File](#-cấu-trúc-file)
- [Công Nghệ Sử Dụng](#-công-nghệ-sử-dụng)
- [API Keys Cần Thiết](#-api-keys-cần-thiết)

---

## Tính Năng Nổi Bật

### AI-Powered Features

#### 1. **Smart Ranking Engine**
- Tự động chấm điểm và sắp xếp kết quả tìm kiếm dựa trên độ phù hợp với hồ sơ người dùng
- Không chỉ sắp xếp theo giá hay đánh giá, mà còn dựa trên sở thích cá nhân
- Hiển thị lý do cụ thể "Tại sao khách sạn này hợp với bạn" (ví dụ: "90% Match - Vì có Spa yên tĩnh")

#### 2. **AI Chatbot Thông Minh**
- Chatbot ghi nhớ lịch sử trò chuyện và hiểu rõ sở thích người dùng
- Tư vấn cá nhân hóa dựa trên hồ sơ người dùng (Vibe, Companion, Budget)
- Hỗ trợ tìm kiếm bằng ngôn ngữ tự nhiên
- Phân tích và trích xuất thông tin từ cuộc hội thoại để tìm kiếm chính xác

#### 3. **Auto-Fill Thông Minh**
- Tự động điền bộ lọc (Price, Stars, Amenities) dựa trên preferences của người dùng
- Gợi ý địa điểm dựa trên lịch sử xem khách sạn
- Tự động đề xuất khách sạn phù hợp khi người dùng chưa có lịch sử

#### 4. **Passive Learning System**
- Tự động học và cập nhật Budget và Vibe của người dùng dựa trên lịch sử xem phòng (sau 3-4 lần xem)
- Phân tích amenities để cập nhật preferences (ví dụ: spa/yoga → Healing, gym/hiking → Adventure)
- Cập nhật tự động vibe khi phát hiện pattern trong hành vi người dùng

#### 5. **Genie AI - Đề Xuất Lịch Trình**
- Tạo lịch trình du lịch cá nhân hóa tại khách sạn cụ thể
- Dựa trên vibe và sở thích của người dùng
- Tích hợp trong trang chi tiết khách sạn

#### 6. **AI Tóm Tắt Reviews**
- Tự động tóm tắt tối đa 20 reviews gần nhất của khách sạn
- Giúp người dùng nhanh chóng nắm bắt ý kiến của cộng đồng

#### 7. **So Sánh Khách Sạn với AI**
- So sánh 2-3 khách sạn cùng lúc
- AI tóm tắt và phân tích điểm mạnh/yếu của từng khách sạn

#### 8. **Phân Tích Ảnh & Search Theo Mood**
- Tìm kiếm khách sạn dựa trên mood và phân tích hình ảnh
- Gợi ý khách sạn phù hợp với cảm xúc và mong muốn của người dùng

### Core Features

- **Tìm Kiếm Nâng Cao**: Filter theo địa điểm, mức giá, mức sao, tiện nghi
- **Hệ Thống Đánh Giá**: Người dùng có thể để lại reviews và ratings
- **Yêu Thích**: Lưu danh sách khách sạn yêu thích
- **Lịch Sử Xem**: Theo dõi các khách sạn đã xem
- **Cache Thông Minh**: Cache kết quả tìm kiếm và thông tin khách sạn (tự động reload sau 5 ngày)
- **UI/UX Hiện Đại**: Giao diện trực quan, dễ sử dụng

---


## Cấu Hình Environment Variables

Tạo file `.env` trong thư mục gốc của project với nội dung:

```env
SERPAPI_KEY=your_serpapi_key_here
GEMINI_API_KEY=your_gemini_api_key_here
APP_SECRET=your_secret_key_here
```

**Lưu ý**: 
- Lấy `SERPAPI_KEY` từ [SerpAPI](https://serpapi.com/)
- Lấy `GEMINI_API_KEY` từ [Google AI Studio](https://makersuite.google.com/app/apikey)
- `APP_SECRET` có thể là bất kỳ chuỗi ngẫu nhiên nào (dùng để mã hóa session)

---

## 📖 Hướng Dẫn Sử Dụng

### Đăng Ký & Đăng Nhập

1. Truy cập trang chủ và đăng ký tài khoản mới
2. Đăng nhập lần đầu, bạn sẽ được yêu cầu điền khảo sát nhỏ:
   - **Vibe**: Phong cách du lịch (Luxury, Adventure, Healing, v.v.)
   - **Companion**: Đi cùng ai (Cặp đôi, Gia đình, Bạn bè, v.v.)
   - **Budget**: Ngân sách (Thấp, Trung bình, Cao)

### Tìm Kiếm Khách Sạn

#### Cách 1: Sử Dụng Filter Truyền Thống

1. Chọn **Địa điểm** (bắt buộc)
2. Tùy chọn: Chọn **Mức giá**, **Mức sao**, **Tiện nghi**
3. Bật **AI Auto-fill** để hệ thống tự động điền dựa trên preferences
4. Nhấn "Tìm kiếm"

#### Cách 2: Sử Dụng AI Chatbot

1. Mở chatbot trên trang chủ hoặc trang kết quả
2. Trò chuyện tự nhiên, ví dụ:
   - "Tìm khách sạn ở Đà Lạt có bể bơi"
   - "Khách sạn 4 sao ở Hà Nội giá dưới 2 triệu"
3. Chatbot sẽ tự động phân tích và tìm kiếm

### Xem Chi Tiết Khách Sạn

- Click vào khách sạn để xem thông tin chi tiết
- Xem lý do "Tại sao khách sạn này hợp với bạn"
- Xem AI tóm tắt reviews
- Sử dụng Genie AI để tạo lịch trình du lịch
- Thêm vào yêu thích hoặc để lại review

### So Sánh Khách Sạn

1. Trong trang kết quả, chọn 2-3 khách sạn để so sánh
2. Xem bảng so sánh chi tiết
3. Đọc AI tóm tắt so sánh để đưa ra quyết định

### Quản Lý Yêu Thích & Lịch Sử

- Xem danh sách yêu thích: Menu → My Favorites
- Xem lịch sử: Menu → History

---

## Cấu Trúc File

```
Project/
│
├── .env                          # Environment variables (API keys)
├── .gitignore                    # Git ignore file
├── README.md                     # File này
├── requirements.txt              # Python dependencies
├── run.py                        # Entry point của ứng dụng
├── user_db.db                    # SQLite database (tự động tạo)
│
└── app/                          # Thư mục chính của ứng dụng
    │
    ├── __init__.py               # Flask app factory
    ├── database.py               # Database connection & utilities
    ├── schema.sql                # Database schema
    ├── utils.py                  # Utility functions (AI helpers, scoring)
    │
    ├── blueprints/               # Flask blueprints (routes)
    │   ├── __init__.py
    │   ├── api.py                # API endpoints (chatbot, AI features)
    │   ├── auth.py               # Authentication routes (login, register)
    │   ├── hotel.py              # Hotel search & detail routes
    │   └── main.py               # Main routes (home, profile)
    │
    ├── services/                 # Business logic services
    │   ├── __init__.py
    │   └── search_service.py     # Hotel search service (SerpAPI integration)
    │
    ├── static/                   # Static files (CSS, JS, images)
    │   ├── css/
    │   │   ├── base.css          # Base styles
    │   │   ├── hotel.css         # Hotel page styles
    │   │   └── index.css         # Home page styles
    │   │
    │   └── js/
    │       ├── base.js           # Base JavaScript utilities
    │       ├── hotel.js          # Hotel page JavaScript
    │       └── index.js          # Home page JavaScript
    │
    └── templates/                # Jinja2 templates
        ├── base.html             # Base template
        ├── index.html            # Home page
        │
        ├── auth/
        │   └── profile.html      # User profile page
        │
        ├── hotel/
        │   ├── hotel_detail.html # Hotel detail page
        │   └── hotel_results.html # Search results page
        │
        └── user/
            ├── favorites.html    # Favorites page
            └── history.html      # View history page
```

### Mô Tả Các Thành Phần Chính

#### `app/__init__.py`
- Khởi tạo Flask application
- Đăng ký blueprints
- Cấu hình database và session

#### `app/database.py`
- Quản lý kết nối SQLite
- Các hàm tiện ích cho database operations

#### `app/utils.py`
- Các hàm AI helper: `calculate_match_score()`, `get_ai_preferences()`, `generate_ai_suggestion()`
- Xử lý preferences và scoring logic

#### `app/blueprints/api.py`
- API endpoints cho chatbot
- AI features: tóm tắt reviews, so sánh khách sạn, tạo lịch trình

#### `app/blueprints/hotel.py`
- Routes cho tìm kiếm và xem chi tiết khách sạn
- Xử lý filter và ranking

#### `app/services/search_service.py`
- Tích hợp với SerpAPI
- Xử lý tìm kiếm và cache kết quả

#### Database Schema
- `users`: Thông tin người dùng và preferences
- `favorite_places`: Khách sạn yêu thích
- `search_cache`: Cache kết quả tìm kiếm
- `hotel_cache`: Cache thông tin chi tiết khách sạn
- `user_reviews`: Reviews của người dùng
- `recently_viewed`: Lịch sử xem khách sạn
- `review_summaries`: AI tóm tắt reviews
- `hotel_itineraries`: Lịch trình du lịch được tạo bởi AI

## 🛠 Công Nghệ Sử Dụng

### Backend
- **Flask**: Web framework
- **SQLite**: Database
- **Werkzeug**: Security utilities (password hashing)

### AI & APIs
- **Google Gemini API**: AI chatbot, tóm tắt, so sánh
- **SerpAPI**: Tìm kiếm khách sạn từ Google Hotels

### Frontend
- **HTML5/CSS3**: Giao diện người dùng
- **JavaScript**: Tương tác phía client
- **Jinja2**: Template engine

### Utilities
- **python-dotenv**: Quản lý environment variables
- **Pillow**: Xử lý hình ảnh
- **pandas**: Xử lý dữ liệu (nếu cần)
- **requests**: HTTP requests

---

## API Keys Cần Thiết

### 1. SerpAPI Key
- **Mục đích**: Tìm kiếm khách sạn từ Google Hotels
- **Lấy key**: [https://serpapi.com/](https://serpapi.com/)
- **Documentation**: [https://serpapi.com/google-hotels-api](https://serpapi.com/google-hotels-api)

### 2. Gemini API Key
- **Mục đích**: AI features (chatbot, tóm tắt, so sánh)
- **Lấy key**: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
- **Documentation**: [https://pypi.org/project/google-genai/](https://pypi.org/project/google-genai/)

---

## Notes

- Database sẽ tự động được tạo khi chạy ứng dụng lần đầu
- Cache được tự động reload sau 5 ngày
- Ứng dụng chạy ở chế độ debug mặc định (có thể tắt trong `run.py`)

---

## Tài Liệu Tham Khảo

- [SerpAPI Documentation](https://serpapi.com/google-hotels-api)
- [Google Gemini API](https://pypi.org/project/google-genai/)
- [Flask Documentation](https://flask.palletsprojects.com/)