from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import os

def utcnow_helper():
    return datetime.now(timezone.utc).replace(tzinfo=None)

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
    wing = db.Column(db.String(50), default='Army')
    theme_preference = db.Column(db.String(20), default='system')
    is_approved = db.Column(db.Boolean, default=False)
    cert_a_approved = db.Column(db.Boolean, default=False)
    cert_b_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow_helper)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)

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
    created_at = db.Column(db.DateTime, default=utcnow_helper)

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
    uploaded_at = db.Column(db.DateTime, default=utcnow_helper)

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
    created_at = db.Column(db.DateTime, default=utcnow_helper)

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
    requested_at = db.Column(db.DateTime, default=utcnow_helper)
    note = db.Column(db.String(255), nullable=True)

    __table_args__ = (db.UniqueConstraint('cadet_id', 'date', name='unique_request_cadet_date'),)

    cadet = db.relationship('User', backref=db.backref('attendance_requests', cascade='all, delete-orphan'))

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
    marked_at = db.Column(db.DateTime, default=utcnow_helper)

    __table_args__ = (db.UniqueConstraint('cadet_id', 'date', name='unique_cadet_date'),)

    cadet = db.relationship('User', backref=db.backref('attendances', cascade='all, delete-orphan'))

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

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow_helper)

    def __repr__(self):
        return f'<Contact from {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cadet = db.Column(db.String(100), nullable=False)
    award = db.Column(db.String(200), nullable=False)
    achievement_type = db.Column(db.String(50), nullable=True)
    date = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_helper)

    def __repr__(self):
        return f'<Achievement {self.award}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cadet': self.cadet,
            'award': self.award,
            'type': self.achievement_type,
            'date': self.date,
            'created_at': self.created_at.isoformat()
        }

class Camp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    camp_type = db.Column(db.String(50), default='Annual') # 'National' | 'State' | 'Annual' | 'Special'
    vacancies = db.Column(db.Integer, default=50)
    eligibility = db.Column(db.String(100), default='All')
    status = db.Column(db.String(20), default='open') # 'open' | 'closed'
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_helper)

    def __repr__(self):
        return f'<Camp {self.title}>'

    def to_dict(self):
        try:
            selected_cnt = len([a for a in self.applications if a.status == 'selected'])
        except Exception:
            selected_cnt = 0
        return {
            'id': self.id,
            'title': self.title,
            'location': self.location or 'Not Specified',
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'camp_type': self.camp_type,
            'vacancies': self.vacancies,
            'selected_count': selected_cnt,
            'eligibility': self.eligibility,
            'status': self.status,
            'description': self.description or '',
            'created_at': self.created_at.isoformat()
        }

class CampApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camp_id = db.Column(db.Integer, db.ForeignKey('camp.id'), nullable=False)
    cadet_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=utcnow_helper)
    height = db.Column(db.Float, nullable=True) # cm
    weight = db.Column(db.Float, nullable=True) # kg
    medical_status = db.Column(db.String(50), default='Fit') # 'Fit' | 'Unfit'
    past_camps = db.Column(db.Text, nullable=True) # descriptive
    status = db.Column(db.String(20), default='pending') # 'pending' | 'selected' | 'rejected'
    note = db.Column(db.String(255), nullable=True) # admin note

    __table_args__ = (db.UniqueConstraint('camp_id', 'cadet_id', name='unique_camp_cadet'),)

    camp = db.relationship('Camp', backref=db.backref('applications', cascade='all, delete-orphan'))
    cadet = db.relationship('User', backref=db.backref('camp_applications', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<CampApplication camp={self.camp_id} cadet={self.cadet_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'camp_id': self.camp_id,
            'camp_title': self.camp.title if self.camp else '',
            'camp_type': self.camp.camp_type if self.camp else '',
            'camp_location': self.camp.location if self.camp else '',
            'camp_start': self.camp.start_date.strftime('%Y-%m-%d') if self.camp else '',
            'camp_end': self.camp.end_date.strftime('%Y-%m-%d') if self.camp else '',
            'cadet_id': self.cadet_id,
            'cadet_name': self.cadet.username if self.cadet else '',
            'cadet_first_name': self.cadet.first_name or '',
            'cadet_last_name': self.cadet.last_name or '',
            'cadet_email': self.cadet.email if self.cadet else '',
            'cadet_roll_no': self.cadet.roll_no or '—',
            'cadet_branch': self.cadet.branch or '—',
            'cadet_year': self.cadet.year or '—',
            'applied_at': self.applied_at.isoformat(),
            'height': self.height,
            'weight': self.weight,
            'medical_status': self.medical_status,
            'past_camps': self.past_camps or '',
            'status': self.status,
            'note': self.note or ''
        }

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    endpoint = db.Column(db.String(512), unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_helper)

    user = db.relationship('User', backref=db.backref('push_subscriptions', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<PushSubscription endpoint={self.endpoint[:30]}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'endpoint': self.endpoint,
            'p256dh': self.p256dh,
            'auth': self.auth,
            'created_at': self.created_at.isoformat()
        }

class SmsAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    receiver_phone = db.Column(db.String(20), nullable=False)
    message_title = db.Column(db.String(150), nullable=True, default='NCC Announcement')
    message_body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='simulated')  # 'sent' | 'simulated' | 'failed' | 'scheduled'
    is_read = db.Column(db.Boolean, default=False)
    is_direct = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=utcnow_helper)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    category = db.Column(db.String(50), default='info')  # 'info' | 'warning' | 'success' | 'danger'
    error_message = db.Column(db.String(255), nullable=True)

    # ── Tier 1: Acknowledgement ───────────────────────────────────────
    requires_acknowledgement = db.Column(db.Boolean, default=False)
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    # ── Tier 1: Emergency SOS ────────────────────────────────────────
    is_emergency = db.Column(db.Boolean, default=False)

    # ── Tier 1: Target Group ─────────────────────────────────────────
    target_group = db.Column(db.String(50), nullable=True)  # 'all' | 'army' | 'navy' | 'air' | 'year_1' | 'year_2' | 'year_3' | 'individual'

    # ── Tier 2: Additional Channels ──────────────────────────────────
    email_channel = db.Column(db.Boolean, default=False)
    whatsapp_channel = db.Column(db.Boolean, default=False)

    # ── Tier 2: Recurring Alerts ─────────────────────────────────────
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.String(20), nullable=True)  # 'daily' | 'weekly' | 'monthly'
    recurrence_interval = db.Column(db.Integer, default=1)
    next_recurrence_at = db.Column(db.DateTime, nullable=True)

    # ── Tier 2: Smart Reminders ──────────────────────────────────────
    reminder_hours = db.Column(db.Integer, nullable=True)   # Auto-resend after N hours if unread
    reminder_sent = db.Column(db.Boolean, default=False)

    # ── Tier 2: Expiry ───────────────────────────────────────────────
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('sms_alerts', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<SmsAlert to={self.receiver_phone} status={self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'cadet_name': self.user.username if self.user else 'Broadcast / Unregistered',
            'cadet_first_name': self.user.first_name if self.user else '',
            'cadet_last_name': self.user.last_name if self.user else '',
            'cadet_wing': self.user.wing if self.user else '',
            'cadet_year': self.user.year if self.user else '',
            'receiver_phone': self.receiver_phone,
            'message_title': self.message_title or 'NCC Announcement',
            'message_body': self.message_body,
            'status': self.status,
            'is_read': self.is_read,
            'is_direct': self.is_direct,
            'is_emergency': self.is_emergency or False,
            'requires_acknowledgement': self.requires_acknowledgement or False,
            'is_acknowledged': self.is_acknowledged or False,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'target_group': self.target_group or 'all',
            'email_channel': self.email_channel or False,
            'whatsapp_channel': self.whatsapp_channel or False,
            'is_recurring': self.is_recurring or False,
            'recurrence_type': self.recurrence_type,
            'reminder_hours': self.reminder_hours,
            'reminder_sent': self.reminder_sent or False,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'sent_at': self.sent_at.isoformat(),
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'category': self.category or 'info',
            'error_message': self.error_message or ''
        }

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cadet_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(db.String(50), default='Personal')  # 'Medical' | 'Academic' | 'Personal' | 'Family Emergency' | 'Other'
    reason = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # 'Pending' | 'Approved' | 'Rejected' | 'Cancelled'
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_helper)
    updated_at = db.Column(db.DateTime, default=utcnow_helper, onupdate=utcnow_helper)

    cadet = db.relationship('User', backref=db.backref('leave_requests', cascade='all, delete-orphan'))

    def days_count(self):
        return (self.end_date - self.start_date).days + 1

    def to_dict(self):
        c = self.cadet
        return {
            'id': self.id,
            'cadet_id': self.cadet_id,
            'cadet_name': f"{c.first_name or ''} {c.last_name or ''}".strip() or c.username,
            'cadet_username': c.username,
            'cadet_roll_no': c.roll_no or '—',
            'cadet_branch': c.branch or '—',
            'cadet_year': c.year or '—',
            'cadet_wing': c.wing or 'Army',
            'cadet_email': c.email,
            'leave_type': self.leave_type or 'Personal',
            'reason': self.reason,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'days_count': self.days_count(),
            'status': self.status,
            'comments': self.comments or '',
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else self.created_at.isoformat()
        }

