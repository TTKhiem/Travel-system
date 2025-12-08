from pathlib import Path

from app import create_app, database

app = create_app()

if __name__ == "__main__":
    db_path = Path(app.config["DATABASE"])
    if not db_path.exists():
        with app.app_context():
            database.init_db()
    app.run(debug=True)

