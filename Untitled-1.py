import mysql.connector
from flask import Flask, request, jsonify,render_template
import pandas as pd
app = Flask(__name__)
# db = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="your_password",  
#     database="travel_db"
# )

# cursor = db.cursor()
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/recommendation')
def recommendation():
    return render_template('recommendation.html')

@app.route('/filter', methods=['POST'])
def filter():
    city = request.form['city']
    price_range = request.form['price_range']
    rating_range = str(request.form['rating'])

    # Đọc file CSV
    # df = pd.read_csv('hotels.csv')
    df = pd.read_csv('hotels_vn_1000.csv')
    # Lọc theo city
    filtered = df[df['city'] == city]

    # Lọc theo khoảng giá
    if price_range == "0-500000":
        filtered = filtered[filtered['price_per_night'] <= 500000]
    elif price_range == "500000-1000000":
        filtered = filtered[(filtered['price_per_night'] > 500000) & (filtered['price_per_night'] <= 1000000)]
    elif price_range == "1000000-2000000":
        filtered = filtered[(filtered['price_per_night'] > 1000000) & (filtered['price_per_night'] <= 2000000)]
    else:
        filtered = filtered[filtered['price_per_night'] > 2000000]

    # Lọc theo số sao
    if rating_range:
        min_r, max_r = map(int, rating_range.split('-'))
        filtered = filtered[(filtered['rating'] >= min_r) & (filtered['rating'] <= max_r)]

    # Trả về lại trang cùng kết quả
    return render_template('filter.html', results=filtered.to_dict(orient='records'))
if __name__ == '__main__':
    app.run(debug=True) 