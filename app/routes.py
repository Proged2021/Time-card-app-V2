from flask import (
    Blueprint,
    render_template,
    abort,
    Response,
    flash,
    redirect,
    url_for,
    request,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Course, Student, Attendance, Teacher
from datetime import datetime
try:
    import qrcode
except Exception:
    qrcode = None
from io import BytesIO
from sqlalchemy import cast, Date  # cast, Dateを追加

# Blueprintの定義
main_bp = Blueprint('main', __name__)

# ===============================================
# 0. 基本ルート
# ===============================================

@main_bp.route('/')
def index():
    # とりあえずログインページにリダイレクト
    return redirect(url_for('main.login'))


@main_bp.route('/db_test')
def db_test():
    try:
        db.session.execute(db.text('SELECT 1'))
        return "Database Connection: OK"
    except Exception as e:
        return f"Database Connection Error: {e}", 500


# ===============================================
# 1. 認証ルート (UC-01)
# ===============================================

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = Teacher.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            if username == 'admin':  # adminユーザーの場合
                flash('管理者としてログインしました。', 'success')
                return redirect(url_for('main.admin_dashboard'))
            else:
                flash('ログインしました。', 'success')
                return redirect(url_for('main.login'))
        else:
            flash('ユーザー名またはパスワードが正しくありません。', 'error')

    return render_template('login.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('main.index'))


# ===============================================
# 2. 教師向け：管理画面 (UC-06の起点)
# ===============================================

@main_bp.route('/admin/dashboard')
@login_required  # ログイン必須
def admin_dashboard():
    # ログイン中の教師が担当する授業リストを取得
    teacher_id = current_user.id
    courses = Course.query.filter_by(teacher_id=teacher_id).order_by(
        Course.start_time
    ).all()

    # 画面遷移図の「管理画面」に対応
    return render_template('admin/dashboard.html', courses=courses)


# ===============================================
# 3. 教師向け：出欠確認レポート (UC-06)
# ===============================================

@main_bp.route('/admin/attendance/<int:course_id>', methods=['GET'])
@login_required
def attendance_report(course_id):
    course = Course.query.get_or_404(course_id)

    # ログイン中の教師がその授業の担当者であることを確認（セキュリティチェック）
    if course.teacher_id != current_user.id:
        abort(403)  # 権限がない場合

    # クエリパラメータから日付を取得、なければ本日
    report_date_str = request.args.get(
        'date', datetime.now().strftime('%Y-%m-%d')
    )
    try:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('無効な日付形式です。', 'error')
        report_date = datetime.now().date()
        report_date_str = report_date.strftime('%Y-%m-%d')

    # **本日の出欠データ**を取得（日付でフィルタリング）
    daily_attendances = db.session.query(
        Student.student_id,
        Student.student_name,
        Attendance.status,
        Attendance.scan_time,
    ).outerjoin(
        Attendance,
        db.and_(
            Student.id == Attendance.student_id,
            Attendance.course_id == course_id,
            cast(Attendance.scan_time, Date) == report_date,  # 日付で比較
        ),
    ).all()

    # レポート用データ構造に変換
    report_data = []
    present_count = 0
    late_count = 0

    for student_id, name, status, scan_time in daily_attendances:
        status_display = status if status else '欠席'
        if scan_time:
            scan_time_display = scan_time.strftime('%H:%M:%S')
        else:
            scan_time_display = '-'

        if status == '出席':
            present_count += 1
        elif status == '遅刻':
            late_count += 1

        report_data.append({
            'student_id': student_id,
            'name': name,
            'status': status_display,
            'scan_time': scan_time_display,
        })

    # 統計情報の計算
    total_students = Student.query.count()
    absence_count = total_students - (present_count + late_count)

    return render_template(
        'admin/attendance_report.html',
        course=course,
        report_data=report_data,
        report_date=report_date_str,
        total_students=total_students,
        present_count=present_count,
        late_count=late_count,
        absence_count=absence_count,
    )


# ===============================================
# 4. QRコード生成 (UC-02)
# ===============================================

@main_bp.route('/teacher/qr_code/<int:course_id>')
@login_required
def generate_qr_code(course_id):
    course = Course.query.get_or_404(course_id)

    # QRコードに埋め込むデータ：生徒が出欠登録を行うURL
    # 例: http://localhost:5001/scan/UNIQUE_TOKEN
    qr_data = url_for(
        'main.scan_attendance', token=course.qr_token, _external=True
    )

    # QRコード画像を生成
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)

    # 画像をレスポンスとして返す
    return Response(buffer.getvalue(), mimetype='image/png')


# ===============================================
# 4.5 授業の追加と編集
# ===============================================

@main_bp.route('/admin/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    if request.method == 'POST':
        course_name = request.form.get('course_name')
        start_time_str = request.form.get('start_time')
        tolerance_minutes = request.form.get('tolerance_minutes', type=int)

        try:
            # 時刻文字列（HH:MM）をtime型に変換
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

    return render_template('admin/add_course.html')


# ===============================================
# 5. 生徒向け：出欠登録処理 (UC-03, UC-05)
# ===============================================

@main_bp.route('/scan/<string:token>', methods=['GET', 'POST'])
def scan_attendance(token):
    # 1. QRトークンから授業を特定
    course = Course.query.filter_by(qr_token=token).first_or_404()
    now = datetime.now()

    # 2. 授業が有効期間内かチェック (is_active()は現在常にTrue)
    if not course.is_active():
        flash('この授業の出欠登録期間は終了しました。', 'error')
        return render_template(
            'scan.html', course=course, step=2, message='期間外'
        )

    # 3. GET (生徒IDの入力フォーム表示) - UC-03 ステップ1
    if request.method == 'GET':
        return render_template('scan.html', course=course, step=1)

    # 4. POST (生徒IDの登録処理)
    elif request.method == 'POST':
        student_id_input = request.form.get('student_id')
        student = Student.query.filter_by(student_id=student_id_input).first()

        if not student:
            flash(f'学籍番号 {student_id_input} が見つかりません。', 'error')
            return render_template('scan.html', course=course, step=1)

        # 5. 重複登録チェック (受入条件: 同じ授業時間で複数の登録はできない)
        today = now.date()
        duplicate_check = Attendance.query.filter(
            Attendance.student == student,
            Attendance.course == course,
            cast(Attendance.scan_time, Date) == today,
        ).first()

        if duplicate_check:
            flash('既に本日の出欠が登録されています。', 'warning')
            # ステップ2: 重複登録メッセージ
            return render_template(
                'scan.html', course=course, step=2, status='重複'
            )

        # 6. 出欠ステータス判定 (UC-05)
        status = course.get_status(now)  # '出席' または '遅刻'

        # 7. データベースに記録
        attendance_record = Attendance(
            student=student,
            course=course,
            scan_time=now,
            status=status,
        )
        db.session.add(attendance_record)
        db.session.commit()

        # 8. 完了メッセージ表示 (UC-03: 音と色で知らせる) - ステップ3
        flash(f'出欠登録が完了しました！ ステータス: {status}', 'success')
        return render_template(
            'scan.html', course=course, step=3, status=status
        )
