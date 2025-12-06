CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,       
    email TEXT,           
    phone TEXT,           
    address TEXT,
    preferences TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorite_places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    property_token TEXT NOT NULL, 
    preview_data TEXT,            
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, property_token) -- 1 user 1 favorite khach san
);

CREATE TABLE IF NOT EXISTS hotel_cache (
    token TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_token TEXT NOT NULL,
    review_summaries TEXT,       
    username TEXT NOT NULL,            
    rating INTEGER NOT NULL,            
    comment TEXT,                      
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS recently_viewed (
    user_id INTEGER NOT NULL,
    property_token TEXT NOT NULL,
    preview_data TEXT NOT NULL,
    match_reason TEXT,
    visited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, property_token),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS review_summaries (
    property_token TEXT PRIMARY KEY,
    summary_content TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
