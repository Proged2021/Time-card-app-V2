# run.py

from app import create_app, db
import os
import sys


app = create_app()


def _get_port():
    # 環境変数 PORT またはコマンドライン引数でポートを指定可能
    port = int(os.environ.get('PORT', 5001))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    return port


if __name__ == "__main__":
    with app.app_context():
        # DB接続が確認できたらテーブルを作成
        # 注意: DBコンテナが起動していないとここでエラーになる可能性があります
        db.create_all()

    port = _get_port()
    app.run(host="0.0.0.0", port=port, debug=True)