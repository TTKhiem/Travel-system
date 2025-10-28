from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import sqlite3
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret"

# # --- MySQL connection for users ---
# def get_db_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="123123",     # change if needed
#         database="userdb"
#     )


# --- SQLite connection for users ---
def get_db_connection():
    conn = sqlite3.connect("userdb.db")  # database file stored locally
    conn.row_factory = sqlite3.Row       # allows dict-style row access
    return conn
# -------------------------------
# USER AUTHENTICATION ROUTES
# -------------------------------


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash("Please fill in all fields.")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        if cur.fetchone():
            flash("❌ Username already exists.")
            cur.close(); conn.close()
            return render_template("register.html")

        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        cur.close(); conn.close()
        flash("✅ Account created successfully! Please log in.")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        cur.close(); conn.close()

        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect(url_for('recommendation'))
        else:
            flash("❌ Invalid username or password.")
            return render_template("login.html")
    return render_template("login.html")
@app.route('/')
def home():
    return render_template("index.html")
    

@app.route('/logout')
def logout():
    
    
    session.clear()
    

    flash("You have been logged out.")
    response = redirect(url_for('home'))

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.set_cookie('session', '', expires=0)
    return response

# -------------------------------
# RECOMMENDATION & FILTER ROUTES
# -------------------------------
@app.route('/recommendation')
def recommendation():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('recommendation.html')

@app.route('/filter', methods=['POST'])
def filter_hotels():
    if "user" not in session:
        return redirect(url_for("login"))

    city = request.form['city']
    price_range = request.form['price_range']
    rating_range = str(request.form['rating'])

    df = pd.read_csv('hotels_vn_1000.csv')
    filtered = df[df['city'] == city]

    if price_range == "0-500000":
        filtered = filtered[filtered['price_per_night'] <= 500000]
    elif price_range == "500000-1000000":
        filtered = filtered[(filtered['price_per_night'] > 500000) & (filtered['price_per_night'] <= 1000000)]
    elif price_range == "1000000-2000000":
        filtered = filtered[(filtered['price_per_night'] > 1000000) & (filtered['price_per_night'] <= 2000000)]
    else:
        filtered = filtered[filtered['price_per_night'] > 2000000]

    if rating_range:
        min_r, max_r = map(int, rating_range.split('-'))
        filtered = filtered[(filtered['rating'] >= min_r) & (filtered['rating'] <= max_r)]

    return render_template('filter.html', results=filtered.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
