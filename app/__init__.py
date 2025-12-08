import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, session

from . import database


def create_app():
    """Application factory to build the Flask app with blueprints and config."""
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    base_dir = Path(__file__).resolve().parent.parent
    app.config["DATABASE"] = str(base_dir / "user_db.db")
    app.secret_key = os.getenv("APP_SECRET", "dev-secret")

    database.init_app(app)

    from .blueprints.auth import auth_bp
    from .blueprints.main import main_bp
    from .blueprints.hotel import hotel_bp
    from .blueprints.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(hotel_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_user():
        user_data = None
        if "user_id" in session:
            db = database.get_db()
            row = db.execute(
                "SELECT * FROM users WHERE id = ?", (session["user_id"],)
            ).fetchone()

            if row:
                user_data = dict(row)
                if user_data.get("preferences"):
                    try:
                        import json

                        user_data["preferences_dict"] = json.loads(
                            user_data["preferences"]
                        )
                    except Exception:
                        user_data["preferences_dict"] = {}
                else:
                    user_data["preferences_dict"] = {}

        return dict(user=user_data)

    with app.app_context():
        db_path = Path(app.config["DATABASE"])
        if not db_path.exists():
            database.init_db()

    return app

