from app import create_app, db
from app.models import Teacher, Student, Course, Department 
import os
import sys
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

# ❗修正点: リトライを10回、待機時間を3秒に延長
@retry(stop=stop_after_attempt(10), wait=wait_fixed(3), 
       retry=retry_if_exception_type(OperationalError))
def wait_for_db():
    """DB接続が確立されるまで待機し、テーブルを作成する"""
    print("データベース接続をテスト中...")
    db.session.execute(db.text('SELECT 1'))
    print("データベース接続: OK")
    # 💡 モデル変更のため、一度既存テーブルを削除し、再作成 (開発環境のみ)
    # 本番環境ではマイグレーションツール(Alembic)を使います
    db.drop_all() 
    db.create_all()
    print("データベーステーブル作成: 完了")


def create_initial_data():
    """初期データ（教師、生徒、授業）を投入する"""
    # 既にデータが存在するかチェック (今回はdrop_allするのでこのチェックは無視される)
    if Teacher.query.count() > 0:
        print("初期データは既に存在します。スキップします。")
        return

    print("初期データを投入中...")
    
    # ❗環境変数から管理者アカウント情報を取得
    admin_username = os.environ.get('ADMIN_USERNAME', 'default_admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'default_password')


    # 1. 教師アカウントの作成
    # ❗環境変数から読み込んだ情報で新しい管理者アカウントを登録
    admin_teacher = Teacher(username=admin_username, is_admin=True, name='システム管理者')
    admin_teacher.set_password(admin_password)

    db.session.add_all([admin_teacher])
    db.session.commit()
    print(f"教師アカウント登録: {admin_username}")

    # 2. 生徒の作成 (テスト用 - パスワードと所属情報を追加)
    
    # 💡 パスワードは全て 'studentpass' とする
    student_pass = 'studentpass'
    
    students = [
        # 大学部の生徒
        Student(student_id='U2A001', student_name='山田 太郎', department=Department.UNIVERSITY, grade=2, class_name='A', course='情報科学'),
        Student(student_id='U1B002', student_name='佐藤 花子', department=Department.UNIVERSITY, grade=1, class_name='B', course='経営学'),
        # 専門部の生徒
        Student(student_id='P3C003', student_name='田中 健太', department=Department.PROFESSIONAL, grade=3, class_name='C', course='AI開発'),
        # 高等部の生徒
        Student(student_id='H2D004', student_name='鈴木 美咲', department=Department.HIGH_SCHOOL, grade=2, class_name='D', course='普通科'),
    ]
    
    for s in students:
        s.set_password(student_pass)
        
    db.session.add_all(students)
    db.session.commit()
    print("生徒アカウント登録: 4名 (パスワード: studentpass)")

    # 3. 授業の作成 (テスト用 - 対象所属部を追加)
    course1 = Course(
        course_name='応用プログラミング (大学・専門)', 
        teacher_id=admin_teacher.id, 
        start_time=time(9, 0), 
        tolerance_minutes=15, 
        target_departments=f"{Department.UNIVERSITY},{Department.PROFESSIONAL}" # 💡 大学と専門のみ対象
    )
    course2 = Course(
        course_name='ネットワーク基礎 (大学のみ)', 
        teacher_id=admin_teacher.id, 
        start_time=time(14, 30), 
        tolerance_minutes=5, 
        target_departments=Department.UNIVERSITY # 💡 大学のみ対象
    )
    course3 = Course(
        course_name='基礎英語 (高等部のみ)', 
        teacher_id=admin_teacher.id, 
        start_time=time(16, 0), 
        tolerance_minutes=10, 
        target_departments=Department.HIGH_SCHOOL # 💡 高等部のみ対象
    )
    db.session.add_all([course1, course2, course3])
    db.session.commit()
    print("授業登録: 3件 (対象所属部を設定)")

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
