# Hotel (Release 1.4): Refactored System Structure
## Structure (Version 1.4)
│   .env
│   .gitignore
│   README.md
│   requirements.txt
│   run.py
└───app
    │   database.py
    │   schema.sql
    │   utils.py
    │   __init__.py
    │
    ├───blueprints
    │       api.py
    │       auth.py
    │       hotel.py
    │       main.py
    │       __init__.py
    │
    ├───services
    │       search_service.py
    │       __init__.py
    │
    └───templates
        │   base.html
        │   index.html
        │
        ├───auth
        │       profile.html
        │
        ├───hotel
        │       hotel_detail.html
        │       hotel_results.html
        │
        └───user
                favorites.html
                history.html

## IMPORTANT: CHANGELOG (Version 1.2)
1. Làm khảo sát nhỏ khi người dùng đăng nhập lần đầu (Vibe, Companion, Budget) - **CÓ THỂ SẼ SỬA COMPANION**.
2. Smart Ranking Engine: Thêm Filter tự động chấm điểm và sắp xếp lại kết quả tìm kiếm khách sạn dựa trên độ phù hợp với hồ sơ người dùng (thay vì chỉ sắp xếp theo Giá hay Reviews).
3. Auto-fill bộ lọc **(Price, Stars, Amenities)** khi người dùng để trống (based on **preferences**).
4. Passive: Tự động học và cập nhật lại Budget và Vibe của người dùng dựa trên lịch sử xem phòng (Khoảng 3-4 lần xem).
5. Hiển thị lý do cụ thể "Tại sao khách sạn này hợp với bạn" (Ví dụ: "90% Match - Vì có Spa yên tĩnh") trong trang chi tiết.
6. Chatbot ghi nhớ được lịch sử trò chuyện và biết rõ sở thích người dùng để tư vấn cá nhân hóa.
7. So sánh **2 hoặc 3** khách sạn
8. Fixed bugs trong **hotel_search.py**

## 1.3 updates
1. Thêm **Genie AI** đề xuất lịch trình du lịch tại khách sạn cụ thể (hotel_detail)
2. Chatbot ở **hotel_ressults** nắm thông tin cơ bản của khách sạn gồm có rating và amenities
3. Thêm search theo mood của người dùng và **phân tích ảnh** 

## Cơ chế "Học" của AI
### Cơ chế sort theo preferences trong trang kết quả (Có thể improve)
1. Nếu user thích Luxury và khách sạn >= 4.5 sao: +50 điểm.
2. Nếu user đi Family và khách sạn có "Child-friendly" hoặc "Pool": +40 điểm.
3. Nếu user thích Healing và có "Spa/Garden": +40 điểm.  
=> Danh sách được sắp xếp lại theo điểm số giảm dần. Khách sạn điểm cao nhất: **is_best_match**.
### Cơ chế Passive learning (Có thể improve)
1. Nếu giá xem khách sạn **3 lần** liên tiếp lớn hơn **1tr8** thì sẽ up vibe lên **luxury**
2. Học theo **Amenties**:
- Example: 
+ Tìm từ khóa: spa, yoga, meditation -> Cộng điểm Healing.
+ Tìm từ khóa: gym, hiking, fitness -> Cộng điểm Adventure.  
Điểm của **vibe** nào mà lỡn hơn **4**  thì tự động update vibe của user trong Database.
### Cách Chatbot hiểu ngữ cảnh
- Tự động chèn một đoạn văn bản ẩn (System Prompt) chứa toàn bộ hồ sơ user vào trước câu hỏi: "User này thích Healing, đi Cặp đôi, ngân sách Cao. Hãy tư vấn dựa trên đó".
- Lưu lại lịch sử chat (Session) để user có thể hỏi nối tiếp ("Tìm ở Đà Lạt" -> "Có bể bơi không?" -> Chatbot hiểu đang nói về Đà Lạt).
### Cách mà AI gợi ý trên Filter hoạt động
1. Lấy 10 khách sạn gần nhất từ **recently_viewed**.
2. Đếm thành phố nào xuất hiện nhiều nhất trong địa chỉ của các khách sạn đó.
3. Ưu tiên đưa thành phố đó ra trang chủ
**Notes: Nếu chưa có thành phố nào được xem trước đó thì sẽ tự gợi ý khách sạn dựa trên preferences của user**
## Base features
- API được lưu trong .env (Source tìm hiểu: https://chatgpt.com/share/68fdb9c9-2620-800d-a488-5fe4db254087)
- Display khách sạn
- Tất cả chạy theo nhu cầu trong filter gồm: Địa điểm, Mức giá, Mức sao, Tiện nghi
- AI implemented (**Hỗ trợ trang khách sạn**, **Hỗ trợ so sánh khách sạn**)
- So sánh khách sạn
- Reviews của User

## Known issues:
1. I have skill issue

## Refactored Notes:
1. Tối ưu lại hệ thống search: 
- Chỉ sử dụng SerpAPI hoàn toàn, không còn **GeoApify**
- Không còn xuất file thô local, nạp trực tiếp vào **hotel_results** đối với list khách sạn
- Vào chi tiết khách sạn sẽ tón thêm request fetch **property_token** để lấy thông tin đầy đủ và nạp vào **database** với field **hotel_cache**
- Cache khách sạn sẽ được reload nếu được vào lại sau **5 ngày**
2. Thêm tính năng reviews cho Users và tính năng AI tóm tắt các reviews của Users (Tóm tắt tối đa 20 reviews gần nhất)
3. Trang details của từng khách sạn đã được sửa lại trực quan hơn
4. Fixed My Favorites
5. Remade full UI 
6. Đã thêm tính năng so sánh ~~2~~ 3 khách sạn (+AI tóm tắt so sánh)
7. Thêm một trường filter theo **Amenities** và chỉ bắt buộc chọn Location còn lại **Optional** 
8. Đã fixed được hình ảnh (finally)


# To be updated: (All finished)

# Source tham khảo:
- SerpAPI: https://serpapi.com/google-hotels-api
- GeminiAPI (Google Gen AI SDK): https://pypi.org/project/google-genai/
- Geoapify: https://apidocs.geoapify.com/docs/
- Track Datetime bằng python: https://www.geeksforgeeks.org/python/python-datetime-module/
- Thao tác với JSON bằng python: https://docs.python.org/3/library/json.html
- Misc GPT chat: 
+ Cách pass value của filter từ map(python): https://chatgpt.com/c/68fc9ac9-6928-8322-906b-6612428a8906
+ Convert dữ liệu GPS: https://gemini.google.com/share/8c3e3fb26cf6
+ Chọn API cho phần AI: https://gemini.google.com/share/c6ef28eb4d1a
+ Tạo .env: https://chatgpt.com/share/68fdb9c9-2620-800d-a488-5fe4db254087
+ HTML with Flask: https://chatgpt.com/share/68fdb57c-6310-800d-a189-b73775d45a5f
+ Viết JSON file: https://gemini.google.com/share/b1a2abbedf9a

# Notes: Chưa có file .env
- Tự tạo file ".env" và nhập theo format (Copy paste 2 dòng dưới là đc - tự thay {key}): 
SERPAPI_KEY = {key}  
GEMINI_API_KEY = {key}  
APP_SECRET=ligma
