from app import db
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timedelta


# 所属部の種類を定義
class Department:
    UNIVERSITY = '大学部'
    PROFESSIONAL = '専門部'
    HIGH_SCHOOL = '高等部'

    @classmethod
    def get_code(cls, department):
        codes = {
            cls.UNIVERSITY: 'U',
            cls.PROFESSIONAL: 'P',
            cls.HIGH_SCHOOL: 'H'
        }
        return codes.get(department, 'X')

    @classmethod
    def from_code(cls, code):
        codes = {
            'U': cls.UNIVERSITY,
            'P': cls.PROFESSIONAL,
            'H': cls.HIGH_SCHOOL
        }
        return codes.get(code, None)


# =========================================================
# 認証ユーザー Mixin
# =========================================================

class AuthUserMixin(UserMixin):
    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# =========================================================
# 教師モデル
# =========================================================

class Teacher(db.Model, AuthUserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    courses = db.relationship('Course', backref='teacher', lazy=True)

    def __repr__(self):
        return f'<Teacher {self.username}>'

    def get_id(self):
        return f"teacher-{self.id}"


# =========================================================
# 生徒モデル
# =========================================================

class Student(db.Model, AuthUserMixin):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    class_name = db.Column(db.String(10), nullable=False)
    course = db.Column(db.String(50), nullable=True)
    attendances = db.relationship('Attendance', backref='student', lazy=True)

    def __repr__(self):
        return f'<Student {self.student_id} - {self.student_name}>'

    def get_id(self):
        return f"student-{self.id}"


# =========================================================
# 授業モデル
# =========================================================

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    tolerance_minutes = db.Column(db.Integer, default=10)
    target_departments = db.Column(db.String(255), nullable=False, default=Department.UNIVERSITY)

    attendances = db.relationship('Attendance', backref='course', lazy=True)

    # 💡 修正追加: 出席・遅刻判定ロジック
    def get_status(self, scan_time: datetime) -> str:
        """スキャン時刻と授業開始時刻を比較して出席/遅刻を判定"""
        today_start = datetime.combine(scan_time.date(), self.start_time)
        delta = (scan_time - today_start).total_seconds() / 60  # 分差
        if delta <= self.tolerance_minutes:
            return "出席"
        else:
            return "遅刻"

    # 💡 修正追加: QRの有効期間判定
    def is_active(self) -> bool:
        """授業開始から終了（開始＋90分まで）を有効とみなす"""
        now = datetime.now()
        start = datetime.combine(now.date(), self.start_time)
        end = start + timedelta(minutes=90)
        return start <= now <= end

    def __repr__(self):
        return f'<Course {self.course_name}>'


# =========================================================
# 出欠モデル
# =========================================================

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    scan_time = db.Column(db.DateTime, nullable=False, default=db.func.now())
    status = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.status}>'
