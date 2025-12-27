import json

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .. import database

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    user_data = None
    if "user_id" in session:
        db = database.get_db()
        user_data = db.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    return render_template("index.html", user=user_data, form_type="login", ai_suggestion=None)


@main_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    db = database.get_db()

    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")

        try:
            db.execute(
                """
                UPDATE users
                SET full_name = ?, email = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (full_name, email, phone, address, session["user_id"]),
            )
            db.commit()
            flash("✅ Cập nhật hồ sơ thành công!")
        except Exception as exc: 
            print(exc)
            flash("❌ Có lỗi xảy ra, vui lòng thử lại.")

        return redirect(url_for("main.profile"))

    user_info = db.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    return render_template("auth/profile.html", user_info=user_info)


@main_bp.route("/favorites", methods=["POST"])
def save_favorites():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    token = data.get("property_token")
    preview_info = {
        "name": data.get("name"),
        "image": data.get("image"),
        "price": data.get("price"),
        "address": data.get("address"),
    }
    preview_json = json.dumps(preview_info, ensure_ascii=False)
    user_id = session["user_id"]

    db = database.get_db()
    try:
        db.execute(
            "INSERT OR IGNORE INTO favorite_places (user_id, property_token, preview_data) VALUES (?, ?, ?)",
            (user_id, token, preview_json),
        )
        db.commit()
        return jsonify({"message": "Saved into Favorites:"}), 200
    except Exception as exc: 
        print(exc)
        return jsonify({"message": "Failed!"}), 500


def load_favorites(user_id):
    db = database.get_db()
    rows = db.execute(
        "SELECT property_token, preview_data FROM favorite_places WHERE user_id=?",
        (user_id,),
    ).fetchall()
    favorites = []
    for row in rows:
        data = json.loads(row["preview_data"])
        data["property_token"] = row["property_token"]
        favorites.append(data)
    return favorites


@main_bp.route("/my-favorites")
def my_favorites():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    favorites = load_favorites(session["user_id"])
    return render_template("user/favorites.html", favorites=favorites)


@main_bp.route("/favorites/remove", methods=["POST"])
def remove_favorite():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    token = data.get("property_token")
    user_id = session["user_id"]

    db = database.get_db()
    db.execute(
        "DELETE FROM favorite_places WHERE user_id = ? AND property_token = ?",
        (user_id, token),
    )
    db.commit()
    return jsonify({"message": "Removed"}), 200


@main_bp.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    db = database.get_db()
    rows = db.execute(
        """
        SELECT property_token, preview_data, visited_at
        FROM recently_viewed
        WHERE user_id = ?
        ORDER BY visited_at DESC
        LIMIT 20
        """,
        (session["user_id"],),
    ).fetchall()

    history_list = []
    for row in rows:
        data = json.loads(row["preview_data"])
        data["property_token"] = row["property_token"]
        history_list.append(data)

    return render_template("user/history.html", history_hotels=history_list)


