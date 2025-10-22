from flask import Blueprint
from app import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return "<h1>スマート出欠管理システム - Flaskサーバー稼働中！</h1>"


@main_bp.route('/db_test')
def db_test():
    try:
        db.session.execute(db.text('SELECT 1'))
        return "Database Connection: OK"
    except Exception as e:
        return f"Database Connection Error: {e}", 500
