import sqlite3
from pathlib import Path

import click
from flask import current_app, g
from flask.cli import with_appcontext

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "user_db.db"


def get_db():
    if "db" not in g:
        db_path = current_app.config.get("DATABASE", str(DEFAULT_DB))
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = Path(current_app.root_path) / "schema.sql"
    with open(schema_path, "r", encoding="utf8") as f:
        db.executescript(f.read())
    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    init_db()
    click.echo("Đã khởi tạo database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
