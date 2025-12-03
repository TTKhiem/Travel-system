# Hotel (Beta 2.0)
- API được lưu trong .env (Source tìm hiểu: https://chatgpt.com/share/68fdb9c9-2620-800d-a488-5fe4db254087)
- Xuất khách sạn
- Display khách sạn
- Tất cả chạy theo nhu cầu trong filter (có bug với option dưới 3 sao nhé :skull:)

## Known issues:
1. I have skill issue
2. Lỗi load images chưa sửa được
3. Format frontend của một vài tính năng trong trang **hotel_details.html" hơi lỗi do Bootstrap mới (có gì chỉnh lại sau)

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
6. Đã thêm tính năng so sánh 2 khách sạn (+AI tóm tắt so sánh)
7. Thêm một trường filter theo **Amenities** và chỉ bắt buộc chọn Location còn lại **Optional** 


# To be updated:
~~1. Thêm trường filter để tìm khách sạn *(có thể sẽ tích hợp AI tìm kiếm)* - lọc theo **amenities**~~
~~2. Thêm tính năng so sánh giữa 2 khách sạn **(Để ở ngoài *hotel_results*)**~~
~~4. Favorite places~~
~~5. Cải tiến lại trang **hotel_results**: Thêm tính năng display theo filter theo giá hoặc theo reviews, remake UI~~
6. Filter reviews

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
(Sẵn track giùm số API call nha)

SERPAPI_KEY = {key}  
GEMINI_API_KEY = {key}
