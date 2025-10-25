from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = app.config['SECRET_KEY']

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    #  ログイン設定
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'error'


    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Teacher, Student
        if not isinstance(user_id, str):
            return None
        if user_id.startswith("teacher-"):
            try:
                tid = int(user_id.replace("teacher-", ""))
            except ValueError:
                return None
            return Teacher.query.get(tid)
        elif user_id.startswith("student-"):
            try:
                sid = int(user_id.replace("student-", ""))
            except ValueError:
                return None
            return Student.query.get(sid)
        return None

    from .routes import main_bp
    app.register_blueprint(main_bp)
    from app import models  # noqa: F401

    return app
