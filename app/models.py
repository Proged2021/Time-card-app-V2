from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class Teacher(UserMixin, db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=True)
    course_name = db.Column(db.String(128), nullable=False)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey('teachers.id'), nullable=False
    )
    start_time = db.Column(db.Time, nullable=True)
    qr_token = db.Column(db.String(128), unique=True, nullable=True)
    tolerance_minutes = db.Column(db.Integer, default=15)

    def is_active(self):
        # 簡易チェック: 常に True（必要なら実装を拡張）
        return True

    def get_status(self, now: datetime):
        # 仮実装: 常に '出席' を返す（遅刻判定は必要に応じて実装）
        return '出席'


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(32), unique=True, nullable=False)
    student_name = db.Column(db.String(128), nullable=False)


class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey('students.id'), nullable=False
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey('courses.id'), nullable=False
    )
    scan_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(32), nullable=False)

    # リレーション（オプション）
    student = db.relationship(
        'Student', backref=db.backref('attendances', lazy=True)
    )
    course = db.relationship(
        'Course', backref=db.backref('attendances', lazy=True)
    )

    def __repr__(self):
        return (
            f"<Attendance {self.id} student={self.student_id} "
            f"course={self.course_id}>"
        )
