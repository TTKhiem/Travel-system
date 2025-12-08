import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .. import database

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register_page")
def register_page():
    return render_template("index.html", form_type="register")


@auth_bp.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")

    db = database.get_db()
    try:
        hashed_pw = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (username, password, preferences) VALUES (?, ?, ?)",
            (username, hashed_pw, None),
        )
        user_id = cursor.lastrowid
        db.commit()
        flash("✅ Account created successfully! Please log in.")
        return redirect(url_for("main.home"))
    except sqlite3.IntegrityError:
        flash("❌ Username already exists.")
        return redirect(url_for("auth.register_page"))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Registration error: {exc}")
        flash(f"❌ Có lỗi xảy ra: {str(exc)}")
        return redirect(url_for("auth.register_page"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db = database.get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("main.home"))

        flash("❌ Invalid username or password.")
        return render_template("index.html")
    return render_template("index.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    response = redirect(url_for("main.home"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.set_cookie("session", "", expires=0)
    return response


