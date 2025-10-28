# Hotel (Beta 1.1)
- API được lưu trong .env (Source tìm hiểu: https://chatgpt.com/share/68fdb9c9-2620-800d-a488-5fe4db254087)
- Xuất khách sạn
- Display khách sạn
- Tất cả chạy theo nhu cầu trong filter (có bug với option dưới 3 sao nhé :skull:)
- hotel_results.html vs hotel_detail.html là trang kết quả và trang cá nhân của khách sạn (Nên đọc nghiên cứu HTML chạy với Flask: https://chatgpt.com/share/68fdb57c-6310-800d-a189-b73775d45a5f)

- Chạy file **main.py** là được rồi
- Thư viện cần cài:
- flask: pip install flask hoặc uv pip install flask
- pandas: pip install pandas hoặc uv pip install pandas
- requests: pip install requests hoặc uv pip requests 
- python-dotenv: pip install python-dotenv hoặc uv pip install python-dotenv
<<<<<<< HEAD
- google: pip install google
- google-genai: pip install google-genai
=======
>>>>>>> a88e4f2dd942cefaee3603afc612048143ec008b


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
GEOAPIFY_KEY = {key}
<<<<<<< HEAD
GEMINI_API_KEY = {key}
=======
>>>>>>> a88e4f2dd942cefaee3603afc612048143ec008b
