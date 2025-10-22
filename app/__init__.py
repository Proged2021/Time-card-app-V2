from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # セッション/メッセージ用にSECRET_KEYを設定
    app.secret_key = app.config['SECRET_KEY'] 

    db.init_app(app)

    # Flask-Login の初期化
    login_manager.init_app(app)

    # ユーザーローダーの登録
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Teacher

        return Teacher.query.get(int(user_id))

    # Blueprintの登録
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # モデル定義のロード
    from app import models 

    return app