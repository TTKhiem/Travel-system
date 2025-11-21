import sqlite3
import click
from flask import g, current_app
from flask.cli import with_appcontext

DATABASE = 'user_db.db'
def get_db():
    """Mở một kết nối database mới nếu chưa có cho context hiện tại."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Đóng kết nối database."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Xóa dữ liệu cũ và tạo bảng mới."""
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Xóa dữ liệu hiện có và tạo bảng mới."""
    init_db()
    click.echo('Đã khởi tạo database.')

def init_app(app):
    """Đăng ký các hàm quản lý database với application."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
