import sqlite3

# Kết nối (nếu chưa có file travel.db thì sẽ tự tạo)
conn = sqlite3.connect('travel.db')
cursor = conn.cursor()

# Tạo bảng
cursor.execute('''
CREATE TABLE IF NOT EXISTS destinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    country TEXT,
    description TEXT,
    image_url TEXT
)
''')


cursor.executemany('''
INSERT INTO destinations (name, country, description, image_url)
VALUES (?, ?, ?, ?)
''', [
    ('Ha Long Bay', 'Vietnam', 'A UNESCO World Heritage Site with emerald waters.', 'https://example.com/halong.jpg'),
    ('Kyoto', 'Japan', 'Ancient temples and cherry blossoms.', 'https://example.com/kyoto.jpg'),
    ('Bali', 'Indonesia', 'Beautiful beaches and rice terraces.', 'https://example.com/bali.jpg')
])

conn.commit()
conn.close()

# Tạo database SQLite cho user authentication

conn = sqlite3.connect("userdb.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("Databases and tables created successfully.")