from flask import (
    Blueprint, render_template, abort, Response, flash,
    redirect, url_for, request, session
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Course, Student, Attendance, Teacher
from datetime import datetime
import qrcode
from io import BytesIO
from sqlalchemy import cast, Date
from flask import current_app
import json
import hmac
import hashlib

# Blueprint定義
main_bp = Blueprint('main', __name__)

# ===============================================
# ルート: ログイン関連 (UC-01)
# ===============================================

@main_bp.route('/')
def index():
    return redirect(url_for('main.login'))


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print("="*50)
        print(f"ログイン試行: username={username}, password={password}")

        # 教師ログイン判定
        user = Teacher.query.filter_by(username=username).first()
        print(f"教師検索結果: {user}")
        
        if user:
            print(f"パスワードチェック: {password}")
            is_valid = user.check_password(password)
            print(f"パスワード検証結果: {is_valid}")
            
            if is_valid:
                print("パスワード認証成功 - ログインユーザー設定")
                login_user(user)
                session['user_type'] = 'teacher'
                print("リダイレクト先: admin_dashboard")
                return redirect(url_for('main.admin_dashboard'))
            else:
                print("パスワード認証失敗")

        # 生徒ログイン判定
        user = Student.query.filter_by(student_id=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_type'] = 'student'
            return redirect(url_for('main.student_qrcode_page'))

        flash('ユーザー名またはパスワードが正しくありません。', 'error')
    return render_template('login.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('main.login'))


# ===============================================
# 教師用: ダッシュボード (UC-06)
# ===============================================

@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not isinstance(current_user, Teacher):
        abort(403)

    teacher_id = current_user.id
    courses = Course.query.filter_by(teacher_id=teacher_id).order_by(Course.start_time).all()
    return render_template('admin_dashboard.html', courses=courses)


# ===============================================
# 教師用: 授業追加ページ (UC-04)
# ===============================================

@main_bp.route('/admin/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    if not isinstance(current_user, Teacher):
        abort(403)

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        start_time_str = request.form.get('start_time')
        tolerance_minutes = request.form.get('tolerance_minutes', type=int)

        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            new_course = Course(
                course_name=course_name,
                teacher_id=current_user.id,
                start_time=start_time,
                tolerance_minutes=tolerance_minutes
            )
            db.session.add(new_course)
            db.session.commit()

            flash('授業が追加されました。', 'success')
            return redirect(url_for('main.admin_dashboard'))
        except ValueError:
            flash('無効な時刻形式です。', 'error')

    return render_template('add_course.html')


# ===============================================
# 生徒用: QRコードページ (UC-02)
# ===============================================

@main_bp.route('/student/qrcode')
@login_required
def student_qrcode_page():
    from flask_login import current_user
    from app.models import Student

    # 🧠 デバッグログ追加
    print("=== DEBUG current_user =", current_user)
    print("=== DEBUG type =", type(current_user))
    print("=== DEBUG id =", getattr(current_user, "id", None))
    print("=== DEBUG student_name =", getattr(current_user, "student_name", None))
    print("=== DEBUG is_authenticated =", current_user.is_authenticated)

    if not isinstance(current_user, Student):
        print("⚠️ current_user が Student ではありません -> 403")
        abort(403)

    print("✅ current_user は Student です！")
    return render_template('student_qrcode.html')





@main_bp.route('/student/qrcode/image')
@login_required
def student_qrcode_image():
    """生徒のQRコード画像を生成"""
    if not isinstance(current_user, Student):
        abort(403)

    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    data = {
        "student_id": current_user.student_id,
        "date": current_date
    }
    data_string = json.dumps(data, sort_keys=True)
    secret_key = current_app.config['SECRET_KEY'].encode()
    signature = hmac.new(secret_key, data_string.encode(), hashlib.sha256).hexdigest()
    qr_payload = {**data, "signature": signature}

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(qr_payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return Response(buffer.getvalue(), mimetype='image/png')

# ===============================================
# 出欠登録 (UC-03, UC-05)
# ===============================================

@main_bp.route('/scan/<int:course_id>', methods=['GET', 'POST'])
def scan_attendance(course_id):
    course = Course.query.get_or_404(course_id)
    now = datetime.now()

    if not course.is_active():
        flash('この授業の出欠登録期間は終了しました。', 'error')
        return render_template('scan.html', course=course, step=2, message='期間外')

    if request.method == 'GET':
        return render_template('scan.html', course=course, step=1)

    try:
        qr_data = json.loads(request.form.get('student_id'))
        student_id = qr_data.get('student_id')
        date = qr_data.get('date')
        signature = qr_data.get('signature')
    except Exception:
        flash('QRコードが不正です', 'error')
        return render_template('scan.html', course=course, step=1)

    today = datetime.now().strftime("%Y-%m-%d")
    if date != today:
        flash('QRコードの有効期限が切れています', 'error')
        return render_template('scan.html', course=course, step=1)

    data = {"student_id": student_id, "date": date}
    data_string = json.dumps(data, sort_keys=True)
    secret_key = current_app.config['SECRET_KEY'].encode()
    expected_signature = hmac.new(secret_key, data_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        flash('QRコードが改ざんされています', 'error')
        return render_template('scan.html', course=course, step=1)

    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        flash(f'学籍番号 {student_id} が見つかりません。', 'error')
        return render_template('scan.html', course=course, step=1)

    # 同一授業・同一日で重複登録防止
    today = now.date()
    duplicate = Attendance.query.filter(
        Attendance.student == student,
        Attendance.course == course,
        cast(Attendance.scan_time, Date) == today
    ).first()

    if duplicate:
        flash('既に本日の出欠が登録されています。', 'warning')
        return render_template('scan.html', course=course, step=2, status='重複')

    status = course.get_status(now)
    attendance_record = Attendance(
        student=student, course=course, scan_time=now, status=status
    )
    db.session.add(attendance_record)
    db.session.commit()

    flash(f'出欠登録完了！ ステータス: {status}', 'success')
    return render_template('scan.html', course=course, step=3, status=status)
