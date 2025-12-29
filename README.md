# Ligma - LigmaStay
### Computational Thinking Project
**Ho Chi Minh University of Science - Faculty of Information and Technology**

---

> A smart and personalized hotel recommendation system built for the **Computational Thinking** course.

**LigmaStay** applies computational concepts to solve real-world travel problems. By integrating Generative AI (Gemini) with traditional search algorithms, it can provide users with personalized hotel results based on their unique "vibe," budget, and travel companions, rather than just raw data.

### Instructors
This project was developed under the guidance and supervision of:
1.  **Mr Le Ngoc Thanh**
2.  **Mr Nguyen Thanh Tinh**
3.  **Mr Huynh Lam Hai Dang**

### Group Members
This project was developed by following members from **Ligma** group:
1.  **24127232 - Le Phung Son**
2.  **24127497 - Doan Hong Phuc**
3.  **24127547 - Tran Ho Phuc Thinh**
4.  **24127473 - Dao Thanh Nhan**
5.  **24127585 - Chau Dung Van**
6.  **24127322 - Phan Nhat Anh**
7.  **24127058 - Tiet Trong Khiem**
## 📋 Table of Contents

- [Key Features](#-key-features)
- [Usage Guide](#-usage-guide)
- [File Structure](#-file-structure)
- [Technologies Used](#-technologies-used)
- [Required API Keys](#-required-api-keys)

---

## Key Features

### AI-Powered Features

#### 1. **Smart Ranking Engine**
- Automatically scores and ranks search results based on relevance to the user profile.
- Not just sorted by price or rating, but prioritizing personal preferences.
- Displays specific reasons "Why this hotel suits you" (e.g., "90% Match - Because it has a quiet Spa").

#### 2. **Smart AI Chatbot**
- Chatbot remembers conversation history and deeply understands user preferences.
- Provides personalized advice based on the user profile (Vibe, Companion, Budget).
- Supports natural language search.
- Analyzes and extracts information from conversations to execute accurate searches.

#### 3. **Smart Auto-Fill**
- Automatically fills filters (Price, Stars, Amenities) based on user preferences.
- Suggests locations based on viewing history.
- Automatically suggests suitable hotels when the user has no history.

#### 4. **Passive Learning System**
- Automatically learns and updates Budget and Vibe based on room viewing history (activates after 3-4 views).
- Analyzes amenities to update preferences (e.g., spa/yoga → Healing, gym/hiking → Adventure).
- Automatically updates vibe when detecting patterns in user behavior.

#### 5. **Genie AI - Itinerary Suggestions**
- Generates personalized travel itineraries for specific hotels.
- Based on the user's vibe and interests.
- Integrated directly into the hotel detail page.

#### 6. **AI Review Summarization**
- Automatically summarizes up to the 20 most recent reviews for a hotel.
- Helps users quickly grasp community opinions without reading everything.

#### 7. **AI Hotel Comparison**
- Compare 2-3 hotels simultaneously.
- AI summarizes and analyzes the strengths/weaknesses of each hotel side-by-side.

#### 8. **Image Analysis & Mood Search**
- Search for hotels based on mood and image analysis.
- Suggests hotels matching the user's current emotions and desires.

### Core Features

- **Advanced Search**: Filter by location, price, star rating, and amenities.
- **Review System**: Users can leave reviews and ratings.
- **Favorites**: Save a list of favorite hotels.
- **View History**: Track previously viewed hotels.
- **Smart Cache**: Caches search results and hotel information (automatically reloads after 5 days).
- **Modern UI/UX**: Intuitive and easy-to-use interface.

---

## Environment Variables Configuration

Create a `.env` file in the project root directory with the following content:

```env
SERPAPI_KEY=your_serpapi_key_here
GEMINI_API_KEY=your_gemini_api_key_here
APP_SECRET=your_secret_key_here
```
**Note**: 
- Get `SERPAPI_KEY` from [SerpAPI](https://serpapi.com/)
- Get `GEMINI_API_KEY` from [Google AI Studio](https://makersuite.google.com/app/apikey)
- `APP_SECRET` can be any random string (used for session encryption only)

---

## 📖 Usage Guide

### Registration & Login

1. Access the homepage and register a new account.
2. Upon first login, you will be asked to complete a short survey:
   - **Vibe**: Travel style (Luxury, Adventure, Healing, etc.)
   - **Companion**: Who you are traveling with (Couple, Family, Friends, etc.)
   - **Budget**: Your budget range (Low, Medium, High)

### Searching for Hotels

#### Method 1: Using Traditional Filters

1. Select **Location** (required).
2. Optional: Select **Price**, **Star Rating**, **Amenities**.
3. Enable **AI Auto-fill** to let the system automatically fill fields based on preferences.
4. Click "Search".

#### Method 2: Using AI Chatbot

1. Open the chatbot on the homepage or results page.
2. Chat naturally, for example:
   - "Find a hotel in Da Lat with a swimming pool."
   - "4-star hotel in Hanoi under 2 million VND."
3. The chatbot will automatically analyze and perform the search.

### Viewing Hotel Details

- Click on a hotel to view detailed information.
- View "Why this hotel suits you" reasons.
- Read AI-summarized reviews.
- Use Genie AI to generate a travel itinerary.
- Add to favorites or leave a review.

### Comparing Hotels

1. On the results page, select 2-3 hotels to compare.
2. View the detailed comparison table.
3. Read the AI summary of the comparison to make a decision.

### Managing Favorites & History

- View Favorites: Menu → My Favorites
- View History: Menu → History

---

## File structure

```
Project/
│
├── .env                          # Environment variables (API keys)
├── .gitignore                    # Git ignore file
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── run.py                        # Entry point của ứng dụng
├── user_db.db                    # SQLite database (automatically created)
│
└── app/                          # Main folder
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

### Component Descriptions

#### `app/__init__.py`
- Initializes the Flask application.
- Registers blueprints.
- Configures database and sessions.

#### `app/database.py`
- Manages SQLite connections.
- Utility functions for database operations.

#### `app/utils.py`
- AI helper functions: `calculate_match_score()`, `get_ai_preferences()`, `generate_ai_suggestion()`.
- Handles preferences and scoring logic.

#### `app/blueprints/api.py`
- API endpoints for the chatbot.
- AI features: review summarization, hotel comparison, itinerary generation.

#### `app/blueprints/hotel.py`
- Routes for searching and viewing hotel details.
- Handles filtering and ranking.

#### `app/services/search_service.py`
- Integration with SerpAPI.
- Handles search logic and result caching.

#### Database Schema
- `users`: User information and preferences.
- `favorite_places`: Favorite hotels.
- `search_cache`: Search result cache.
- `hotel_cache`: Hotel detail cache.
- `user_reviews`: User reviews.
- `recently_viewed`: Hotel viewing history.
- `review_summaries`: AI review summaries.
- `hotel_itineraries`: AI-generated travel itineraries.

## 🛠 Technologies Used

### Backend
- **Flask**: Web framework
- **SQLite**: Database
- **Werkzeug**: Security utilities (password hashing)

### AI & APIs
- **Google Gemini API**: AI chatbot, summarization, comparison
- **SerpAPI**: Hotel search from Google Hotels

### Frontend
- **HTML5/CSS3**: User Interface
- **JavaScript**: Client-side interactivity
- **Jinja2**: Template engine

### Utilities
- **python-dotenv**: Environment variable management
- **Pillow**: Image processing
- **pandas**: Data processing (if needed)
- **requests**: HTTP requests

---

## Required API Keys

### 1. SerpAPI Key
- **Purpose**: Searching for hotels via Google Hotels.
- **Get Key**: [https://serpapi.com/](https://serpapi.com/)
- **Documentation**: [https://serpapi.com/google-hotels-api](https://serpapi.com/google-hotels-api)

### 2. Gemini API Key
- **Purpose**: AI features (chatbot, summaries, comparisons).
- **Get Key**: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
- **Documentation**: [https://pypi.org/project/google-genai/](https://pypi.org/project/google-genai/)

---

## Notes

- The database is automatically created when running the application for the first time.
- Cache for hotel details is automatically reloaded after 5 days.
- The application runs in debug mode by default (can be disabled in `run.py`).

---

## References

- [SerpAPI Documentation](https://serpapi.com/google-hotels-api)
- [Google Gemini API](https://pypi.org/project/google-genai/)
- [Flask Documentation](https://flask.palletsprojects.com/)