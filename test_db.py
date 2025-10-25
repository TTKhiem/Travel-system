# filepath: d:\Travel system\test_db.py
import sqlite3

conn = sqlite3.connect('D:\\Travel system\\travel.db') # Use double backslashes or forward slashes
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS destinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    country TEXT
)
""")

cursor.execute("SELECT * FROM destinations")
for row in cursor.fetchall():
    print(row)

conn.close()