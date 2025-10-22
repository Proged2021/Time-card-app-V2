import os


class Config:
    # SECRET_KEYは環境変数から取得
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # DATABASE_URLも環境変数から取得（Docker Composeで設定）
    # 開発中はデフォルトでローカルの SQLite を使う
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///./{os.path.basename(os.getcwd())}.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False