from app import create_app, db
from app.models import Teacher, Student, Course
import os
import sys
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)
from sqlalchemy.exc import OperationalError
from datetime import time

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

# =========================================================
# 💡 Docker起動時のDB接続待機処理
# =========================================================

# OperationalErrorが発生した場合、最大5回、2秒間隔でリトライする
@retry(stop=stop_after_attempt(5), wait=wait_fixed(2), retry=retry_if_exception_type(OperationalError))
def wait_for_db():
    """DB接続が確立されるまで待機し、テーブルを作成する"""
    print("データベース接続をテスト中...")
    db.session.execute(db.text('SELECT 1'))
    print("データベース接続: OK")
    db.create_all()
    print("データベーステーブル作成: 完了")


def create_initial_data():
    """初期データ（教師、生徒、授業）を投入する"""
    # 既にデータが存在するかチェック
    if Teacher.query.count() > 0:
        print("初期データは既に存在します。スキップします。")
        return

    print("初期データを投入中...")
    
    # ❗環境変数から管理者アカウント情報を取得
    admin_username = 'admin'  # 固定値を使用
    admin_password = 'wossyc-qorben-2fyztI'  # 固定値を使用

    # 1. 教師アカウントの作成
    teacher1 = Teacher(username='teacher1', name='テスト教師')
    teacher1.set_password('password')
    
    # 管理者アカウントを登録
    admin_teacher = Teacher(username=admin_username, is_admin=True, name='システム管理者')
    admin_teacher.set_password(admin_password)

    db.session.add_all([teacher1, admin_teacher])
    db.session.commit()
    print(f"教師アカウント登録: teacher1, {admin_username}")

    # 2. 生徒の作成 (テスト用)
    students = [
        Student(student_id='S001', student_name='山田 太郎'),
        Student(student_id='S002', student_name='佐藤 花子'),
        Student(student_id='S003', student_name='田中 健太'),
        Student(student_id='S004', student_name='鈴木 美咲'),
    ]
    db.session.add_all(students)
    db.session.commit()
    print("生徒アカウント登録: 4名")

    # 3. 授業の作成 (テスト用)
    course1 = Course(
        course_name='応用プログラミング', 
        teacher_id=teacher1.id, 
        start_time=time(9, 0), # 9:00am 開始
        tolerance_minutes=15 # 9:15まで遅刻許容
    )
    course2 = Course(
        course_name='ネットワーク基礎', 
        teacher_id=admin_teacher.id, # 新しい教師を担当に設定
        start_time=time(14, 30), # 14:30pm 開始
        tolerance_minutes=5 # 14:35まで遅刻許容
    )
    db.session.add_all([course1, course2])
    db.session.commit()
    print("授業登録: 2件")

    print("初期データ投入: 完了")


if __name__ == "__main__":
    with app.app_context():
        try:
            # 1. DB接続が確立されるまで待機し、テーブルを作成
            wait_for_db()
            
            # 2. 初期データを投入
            create_initial_data()
            
        except Exception as e:
            print(f"致命的なエラー: データベースの初期化に失敗しました。詳細: {e}")
            sys.exit(1)

    port = _get_port()
    app.run(host="0.0.0.0", port=port, debug=True)