from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # セッション/メッセージ用にSECRET_KEYを設定
    app.secret_key = app.config['SECRET_KEY'] 

    db.init_app(app)

    # Blueprintの登録
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # モデル定義のロード
    from app import models 

    return app