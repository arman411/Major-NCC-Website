from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import os

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    roll_no = db.Column(db.String(30), nullable=True)
    branch = db.Column(db.String(50), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    theme_preference = db.Column(db.String(20), default='system')
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    issued_by = db.Column(db.String(100), default="ANO Office")
    deadline = db.Column(db.DateTime, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    is_new = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notice {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'description': self.description,
            'issued_by': self.issued_by,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'file_path': self.file_path,
            'is_new': self.is_new,
            'created_at': self.created_at.isoformat()
        }

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GalleryItem {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'description': self.description,
            'image_url': f'/images/uploads/{os.path.basename(self.image_path)}' if self.image_path else None,
            'uploaded_at': self.uploaded_at.isoformat()
        }

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    participants = db.Column(db.Integer, default=0)
    is_mandatory = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Event {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start_date': self.start_date.isoformat(),
            'location': self.location,
            'event_type': self.event_type,
            'participants': self.participants,
            'is_mandatory': self.is_mandatory,
            'created_at': self.created_at.isoformat()
        }

class AttendanceRequest(db.Model):
    """Cadet submits a request to be marked present for a given date.
    Admin reviews these when finalizing attendance."""
    id = db.Column(db.Integer, primary_key=True)
    cadet_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=True)

    __table_args__ = (db.UniqueConstraint('cadet_id', 'date', name='unique_request_cadet_date'),)

    cadet = db.relationship('User', backref='attendance_requests')

    def __repr__(self):
        return f'<AttendanceRequest cadet={self.cadet_id} date={self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cadet_id': self.cadet_id,
            'cadet_name': self.cadet.username if self.cadet else '',
            'cadet_email': self.cadet.email if self.cadet else '',
            'date': self.date.strftime('%Y-%m-%d'),
            'requested_at': self.requested_at.isoformat(),
            'note': self.note
        }

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cadet_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='present')  # 'present' or 'absent'
    location = db.Column(db.String(100), nullable=True)
    marked_by_admin = db.Column(db.Boolean, default=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('cadet_id', 'date', name='unique_cadet_date'),)

    cadet = db.relationship('User', backref='attendances')

    def __repr__(self):
        return f'<Attendance cadet={self.cadet_id} date={self.date} status={self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cadet_id': self.cadet_id,
            'cadet_name': self.cadet.username if self.cadet else '',
            'cadet_email': self.cadet.email if self.cadet else '',
            'date': self.date.strftime('%Y-%m-%d'),
            'display_date': self.date.strftime('%d %b %Y'),
            'day': self.date.strftime('%A'),
            'status': self.status,
            'marked_by_admin': self.marked_by_admin,
            'marked_at': self.marked_at.isoformat()
        }
