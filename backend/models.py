from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ──────────────────────────────────────────────
#  Student / Cadet (primary table)
# ──────────────────────────────────────────────
class Student(db.Model):
    """NCC cadet enrollment application."""
    __tablename__ = 'students'

    id            = db.Column(db.Integer, primary_key=True)

    # Personal Details
    first_name    = db.Column(db.String(50),  nullable=False)
    last_name     = db.Column(db.String(50),  nullable=False)
    dob           = db.Column(db.String(20),  nullable=False)   # stored as string YYYY-MM-DD
    gender        = db.Column(db.String(10),  nullable=False)
    phone         = db.Column(db.String(15),  nullable=False)
    email         = db.Column(db.String(120), nullable=False, index=True)
    address       = db.Column(db.Text,        nullable=True)

    # Academic Details
    roll_no       = db.Column(db.String(30),  nullable=False, unique=True, index=True)
    branch        = db.Column(db.String(80),  nullable=False)
    year          = db.Column(db.String(20),  nullable=False)
    institution   = db.Column(db.String(150), default='Govt. Polytechnic Hamirpur (HP)')

    # NCC Details
    ncc_wing      = db.Column(db.String(30),  nullable=False)   # Army / Naval / Air
    prev_experience = db.Column(db.String(100), nullable=True)  # None / A Cert / B Cert
    motivation    = db.Column(db.Text,        nullable=True)
    photo_path    = db.Column(db.String(255), nullable=True)    # path to uploaded photo

    # Admin-managed fields
    status        = db.Column(db.String(20),  default='pending', index=True)  # pending / approved / rejected
    cadet_no      = db.Column(db.String(30),  nullable=True)       # assigned after approval
    remarks       = db.Column(db.Text,        nullable=True)       # ANO remarks
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # linked account

    enrolled_at   = db.Column(db.DateTime,   default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attendances   = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade='all, delete-orphan')
    camp_regs     = db.relationship('CampRegistration', backref='student', lazy=True, cascade='all, delete-orphan')
    certificates  = db.relationship('Certificate', backref='student', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':              self.id,
            'first_name':      self.first_name,
            'last_name':       self.last_name,
            'full_name':       f'{self.first_name} {self.last_name}',
            'dob':             self.dob,
            'gender':          self.gender,
            'phone':           self.phone,
            'email':           self.email,
            'address':         self.address,
            'roll_no':         self.roll_no,
            'branch':          self.branch,
            'year':            self.year,
            'institution':     self.institution,
            'ncc_wing':        self.ncc_wing,
            'prev_experience': self.prev_experience,
            'motivation':      self.motivation,
            'photo_url':       f'/uploads/{self.photo_path}' if self.photo_path else None,
            'status':          self.status,
            'cadet_no':        self.cadet_no,
            'remarks':         self.remarks,
            'enrolled_at':     self.enrolled_at.isoformat() if self.enrolled_at else None,
        }

    def __repr__(self):
        return f'<Student {self.roll_no} - {self.first_name} {self.last_name}>'


# ──────────────────────────────────────────────
#  User (Admin / ANO)
# ──────────────────────────────────────────────
class User(db.Model, UserMixin):
    """
    Admin/Staff users who can manage the portal.
    Roles: admin | suo (Senior Under Officer) | juo (Junior Under Officer) | cadet
    """
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Role-based access control
    role          = db.Column(db.String(20), default='cadet', nullable=False, index=True)
    # role choices: 'admin', 'suo', 'juo', 'cadet'

    # OTP 2-Factor Authentication fields
    otp_code      = db.Column(db.String(10),  nullable=True)   # hashed 6-digit OTP
    otp_expiry    = db.Column(db.DateTime,    nullable=True)    # expiry timestamp
    otp_verified  = db.Column(db.Boolean,     default=False)    # True after OTP confirmed this session

    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def is_admin(self):
        """Backward-compatible property."""
        return self.role == 'admin'

    @property
    def is_suo(self):
        return self.role in ('admin', 'suo')

    @property
    def is_juo(self):
        return self.role in ('admin', 'suo', 'juo')

    def can_mark_attendance(self):
        """Admins and SUOs can mark attendance."""
        return self.role in ('admin', 'suo')

    def can_post_notices(self):
        """Admins and SUOs can post notices."""
        return self.role in ('admin', 'suo')

    def to_dict(self):
        return {
            'id':         self.id,
            'username':   self.username,
            'email':      self.email,
            'role':       self.role,
            'is_admin':   self.is_admin,
            'is_suo':     self.is_suo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'


# ──────────────────────────────────────────────
#  Notice Board
# ──────────────────────────────────────────────
class Notice(db.Model):
    __tablename__ = 'notices'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(150), nullable=False)
    category    = db.Column(db.String(50),  nullable=False, index=True)  # Camp / Exam / Urgent / General
    description = db.Column(db.Text,        nullable=False)
    issued_by   = db.Column(db.String(100), default='ANO Office')
    deadline    = db.Column(db.DateTime,    nullable=True)
    file_path   = db.Column(db.String(255), nullable=True)
    is_new      = db.Column(db.Boolean,     default=True)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'title':       self.title,
            'category':    self.category,
            'description': self.description,
            'issued_by':   self.issued_by,
            'deadline':    self.deadline.isoformat() if self.deadline else None,
            'file_url':    f'/uploads/{self.file_path}' if self.file_path else None,
            'file_path':   self.file_path,  # for admin use
            'is_new':      self.is_new,
            'created_at':  self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Notice {self.title}>'


# ──────────────────────────────────────────────
#  Gallery
# ──────────────────────────────────────────────
class GalleryItem(db.Model):
    __tablename__ = 'gallery_items'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(100), nullable=False)
    category    = db.Column(db.String(50),  nullable=False, index=True)  # Camps / Social / Campus / Parade
    description = db.Column(db.String(255), nullable=True)
    image_path  = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'title':       self.title,
            'category':    self.category,
            'description': self.description,
            'image_url':   f'/uploads/{self.image_path}',
            'image_path':  self.image_path,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

    def __repr__(self):
        return f'<GalleryItem {self.title}>'


# ──────────────────────────────────────────────
#  Camps
# ──────────────────────────────────────────────
class Camp(db.Model):
    __tablename__ = 'camps'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    location    = db.Column(db.String(150), nullable=False)
    camp_type   = db.Column(db.String(50),  nullable=False)  # Annual Training / Republic Day / etc.
    start_date  = db.Column(db.String(20),  nullable=False)
    end_date    = db.Column(db.String(20),  nullable=False)
    description = db.Column(db.Text,        nullable=True)
    is_upcoming = db.Column(db.Boolean,     default=True)
    capacity    = db.Column(db.Integer,     default=50)      # max cadets allowed
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    # Relationships
    registrations = db.relationship('CampRegistration', backref='camp', lazy=True, cascade='all, delete-orphan')

    @property
    def registered_count(self):
        return len(self.registrations)

    def to_dict(self):
        return {
            'id':               self.id,
            'name':             self.name,
            'location':         self.location,
            'camp_type':        self.camp_type,
            'start_date':       self.start_date,
            'end_date':         self.end_date,
            'description':      self.description,
            'is_upcoming':      self.is_upcoming,
            'capacity':         self.capacity,
            'registered_count': self.registered_count,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Camp {self.name}>'


# ──────────────────────────────────────────────
#  Achievements
# ──────────────────────────────────────────────
class Achievement(db.Model):
    __tablename__ = 'achievements'

    id          = db.Column(db.Integer, primary_key=True)
    cadet_name  = db.Column(db.String(100), nullable=False)
    title       = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text,        nullable=True)
    year        = db.Column(db.Integer,     nullable=False)
    level       = db.Column(db.String(50),  nullable=False)  # State / National / International
    image_path  = db.Column(db.String(255), nullable=True)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'cadet_name':  self.cadet_name,
            'title':       self.title,
            'description': self.description,
            'year':        self.year,
            'level':       self.level,
            'image_url':   f'/uploads/{self.image_path}' if self.image_path else None,
            'image_path':  self.image_path,
            'created_at':  self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Achievement {self.cadet_name} - {self.title}>'


# ──────────────────────────────────────────────
#  Contact Messages
# ──────────────────────────────────────────────
class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=False)
    phone      = db.Column(db.String(15),  nullable=True)
    subject    = db.Column(db.String(150), nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    is_read    = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':         self.id,
            'name':       self.name,
            'email':      self.email,
            'phone':      self.phone,
            'subject':    self.subject,
            'message':    self.message,
            'is_read':    self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ContactMessage from {self.name}>'


# ═════════════════════════════════════════════════════════════════
#  NEW MODULES: Attendance, CampRegistration, AuditLog, Certificate
# ═════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────
#  Attendance Record
# ──────────────────────────────────────────────
class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    date        = db.Column(db.String(20), nullable=False, index=True) # YYYY-MM-DD
    parade_type = db.Column(db.String(50), nullable=False) # Drill / Theory / Camp / Firing
    present     = db.Column(db.Boolean, default=False)
    remarks     = db.Column(db.String(150), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # enforce unique attendance per cadet per day
    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='uq_attendance_student_date'),
    )

    def to_dict(self):
        return {
            'id':          self.id,
            'student_id':  self.student_id,
            'student_name': self.student.first_name + ' ' + self.student.last_name if self.student else None,
            'roll_no':     self.student.roll_no if self.student else None,
            'date':        self.date,
            'parade_type': self.parade_type,
            'present':     self.present,
            'remarks':     self.remarks,
        }


# ──────────────────────────────────────────────
#  Camp Registration
# ──────────────────────────────────────────────
class CampRegistration(db.Model):
    __tablename__ = 'camp_registrations'

    id            = db.Column(db.Integer, primary_key=True)
    camp_id       = db.Column(db.Integer, db.ForeignKey('camps.id'), nullable=False, index=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    status        = db.Column(db.String(20), default='registered') # registered, accepted, rejected, cancelled
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    # one registration per cadet per camp
    __table_args__ = (
        db.UniqueConstraint('camp_id', 'student_id', name='uq_camp_reg_student'),
    )

    def to_dict(self):
        return {
            'id':            self.id,
            'camp_id':       self.camp_id,
            'camp_name':     self.camp.name if self.camp else None,
            'student_id':    self.student_id,
            'student_name':  self.student.first_name + ' ' + self.student.last_name if self.student else None,
            'roll_no':       self.student.roll_no if self.student else None,
            'status':        self.status,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
        }


# ──────────────────────────────────────────────
#  Audit Log
# ──────────────────────────────────────────────
class AuditLog(db.Model):
    """Tracks admin actions for accountability."""
    __tablename__ = 'audit_logs'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # null if system action
    action      = db.Column(db.String(100), nullable=False) # e.g., "APPROVED_STUDENT", "DELETED_NOTICE"
    target_type = db.Column(db.String(50), nullable=True)  # e.g., "Student", "Notice"
    target_id   = db.Column(db.String(50), nullable=True)  # ID of the targeted record
    details     = db.Column(db.Text, nullable=True)        # JSON string or plain text
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user        = db.relationship('User', backref='admin_logs', lazy=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'user_id':     self.user_id,
            'username':    self.user.username if self.user else 'System',
            'action':      self.action,
            'target_type': self.target_type,
            'target_id':   self.target_id,
            'details':     self.details,
            'timestamp':   self.timestamp.isoformat() if self.timestamp else None,
        }


# ──────────────────────────────────────────────
#  Document Vault
# ──────────────────────────────────────────────
class Document(db.Model):
    __tablename__ = 'documents'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    doc_type    = db.Column(db.String(100), nullable=False) # Aadhar, Medical Certificate, Bank Passbook, etc.
    file_path   = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status      = db.Column(db.String(20), default='pending') # pending, verified, rejected
    
    student     = db.relationship('Student', backref='documents', lazy=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'student_id':  self.student_id,
            'doc_type':    self.doc_type,
            'file_url':    f'/uploads/{self.file_path}' if self.file_path else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'status':      self.status,
        }

# ──────────────────────────────────────────────
#  Helpdesk Query
# ──────────────────────────────────────────────
class HelpdeskQuery(db.Model):
    __tablename__ = 'helpdesk_queries'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject     = db.Column(db.String(150), nullable=False)
    message     = db.Column(db.Text, nullable=False)
    status      = db.Column(db.String(20), default='Open') # Open, Closed, Resolved
    response    = db.Column(db.Text, nullable=True) # Admin's response
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student     = db.relationship('Student', backref='queries', lazy=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'student_id':  self.student_id,
            'subject':     self.subject,
            'message':     self.message,
            'status':      self.status,
            'response':    self.response,
            'created_at':  self.created_at.isoformat() if self.created_at else None,
            'updated_at':  self.updated_at.isoformat() if self.updated_at else None,
        }

# ──────────────────────────────────────────────
#  Certificate
# ──────────────────────────────────────────────
class Certificate(db.Model):
    __tablename__ = 'certificates'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    cert_type   = db.Column(db.String(50), nullable=False) # Enrollment / A / B / C
    issued_on   = db.Column(db.DateTime, default=datetime.utcnow)
    file_path   = db.Column(db.String(255), nullable=True) # Path to generated PDF

    def to_dict(self):
        return {
            'id':         self.id,
            'student_id': self.student_id,
            'cert_type':  self.cert_type,
            'issued_on':  self.issued_on.isoformat() if self.issued_on else None,
            'file_url':   f'/certificates/{self.file_path}' if self.file_path else None,
        }


# ──────────────────────────────────────────────
#  Cadet Points (Gamification / Leaderboard)
# ──────────────────────────────────────────────
class CadetPoints(db.Model):
    """Records individual point awards for cadets."""
    __tablename__ = 'cadet_points'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    points      = db.Column(db.Integer, nullable=False, default=0)
    reason      = db.Column(db.String(150), nullable=False)  # e.g. 'Attendance', 'Camp Accepted'
    awarded_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # None = auto-system
    awarded_at  = db.Column(db.DateTime, default=datetime.utcnow)

    student     = db.relationship('Student', backref='point_records', lazy=True)
    awarder     = db.relationship('User', backref='awarded_points', lazy=True)

    def to_dict(self):
        return {
            'id':         self.id,
            'student_id': self.student_id,
            'points':     self.points,
            'reason':     self.reason,
            'awarded_at': self.awarded_at.isoformat() if self.awarded_at else None,
        }


# ──────────────────────────────────────────────
#  Study Material Hub
# ──────────────────────────────────────────────
class StudyMaterial(db.Model):
    """PDF study materials uploaded by Admin/SUO for cadets."""
    __tablename__ = 'study_materials'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(150), nullable=False)
    # Categories: B-Certificate | C-Certificate | General | Physical Training | Map Reading
    category    = db.Column(db.String(80),  nullable=False, index=True)
    description = db.Column(db.Text,        nullable=True)
    file_path   = db.Column(db.String(255), nullable=False)  # relative path under uploads/
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader    = db.relationship('User', backref='uploaded_materials', lazy=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'title':       self.title,
            'category':    self.category,
            'description': self.description,
            'file_url':    f'/uploads/{self.file_path}' if self.file_path else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
