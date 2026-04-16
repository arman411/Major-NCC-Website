"""
NCC Unit – Govt. Polytechnic Hamirpur (HP)
Backend REST API  ·  Flask + SQLAlchemy + Flask-Login
"""

import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import logging
from flask_migrate import Migrate
from flask_caching import Cache
from PIL import Image
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config import config
from models import (
    db, Student, User, Notice, GalleryItem,
    Camp, Achievement, ContactMessage,
    AttendanceRecord, CampRegistration, AuditLog, Certificate,
    Document, HelpdeskQuery, CadetPoints, StudyMaterial
)
from email_utils import send_enrollment_confirmation, send_status_update, send_contact_autoreply
from pdf_utils import generate_enrollment_certificate
from functools import wraps
import random
import hashlib
from flask_mail import Message

# Import new utilities
import excel_utils
import qr_utils

from email_utils import send_enrollment_confirmation, send_status_update, send_contact_autoreply # type: ignore
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

# ─────────────────────────────
#  App Bootstrap
# ─────────────────────────────
app = Flask(__name__)
app.config.from_object(config)

CORS(app, supports_credentials=True, origins=[
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
])

# rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

db.init_app(app)
migrate = Migrate(app, db)
cache = Cache(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'success': False, 'message': 'Authentication required'}), 401

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CERT_FOLDER'], exist_ok=True)

# ─────────────────────────────
#  Helpers
# ─────────────────────────────
def allowed_file(filename):
    return ('.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])

def save_upload(file_field_name):
    f = request.files.get(file_field_name)
    if f and f.filename and allowed_file(f.filename):
        ext = f.filename.rsplit('.', 1)[1].lower()
        fname = f"{uuid.uuid4().hex[:12]}_{secure_filename(f.filename)}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        f.save(path)
        
        # Resize if image
        if ext in {'png', 'jpg', 'jpeg', 'webp'}:
            try:
                img = Image.open(path)
                if img.width > 1200:
                    wpercent = (1200 / float(img.width))
                    hsize = int((float(img.height) * float(wpercent)))
                    img = img.resize((1200, hsize), Image.Resampling.LANCZOS)
                    img.save(path)
            except Exception as e:
                logger.error(f"Image resize failed: {e}")
                
        return fname
    return None

def delete_upload(filename):
    if filename:
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(path):
            os.remove(path)

def paginate_query(query):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': [item.to_dict() for item in paginated.items],
        'pagination': {
            'page': paginated.page,
            'per_page': paginated.per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    }

def log_action(action, target_type=None, target_id=None, details=None):
    user_id = current_user.id if current_user.is_authenticated else None
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details=details
    )
    db.session.add(log)
    db.session.commit()

# ─────────────────────────────
#  Serve Frontend
# ─────────────────────────────
@app.route('/', defaults={'path': 'index.html'})
@app.route('/frontend/', defaults={'path': 'index.html'})
@app.route('/frontend/<path:path>')
def serve_frontend(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/certificates/<path:filename>')
@login_required # only authenticated users can view certs directly via URL
def serve_certificate(filename):
    return send_from_directory(app.config['CERT_FOLDER'], filename)

# ─────────────────────────────
#  RBAC Decorator
# ─────────────────────────────
def require_role(*roles):
    """Decorator to require a specific role(s) to access an endpoint."""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            if current_user.role not in roles and 'admin' not in roles:
                # admin automatically gets access to everything
                if current_user.role != 'admin':
                    return jsonify({'success': False, 'message': f'Role {roles} required'}), 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# ═══════════════════════════════════════════════
#  AUTH  ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.get_json(silent=True) or request.form
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        log_action('FAILED_LOGIN', 'User', email, 'Invalid credentials')
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    user.otp_code = generate_password_hash(otp, method='pbkdf2:sha256')
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    user.otp_verified = False
    db.session.commit()

    # Send OTP Email
    try:
        from email_utils import send_email # type: ignore
        subject = "Your NCC Login OTP"
        body = f"Hello {user.username},\n\nYour login OTP is: {otp}\nThis code is valid for 5 minutes.\n\nRegards,\nNCC Admin"
        send_email(subject, user.email, body)
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")

    # Don't log them in firmly yet; frontend must hit verify-otp
    return jsonify({'success': True, 'otp_required': True, 'email': user.email, 'message': 'OTP sent to email'}), 200

@app.route('/api/auth/verify-otp', methods=['POST'])
@limiter.limit("10 per minute")
def verify_otp():
    data = request.get_json(silent=True) or request.form
    email = data.get('email', '').strip()
    otp = data.get('otp', '').strip()

    if not email or not otp:
        return jsonify({'success': False, 'message': 'Email and OTP required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.otp_code or not user.otp_expiry:
        return jsonify({'success': False, 'message': 'OTP flow not initiated'}), 400

    if datetime.utcnow() > user.otp_expiry:
        return jsonify({'success': False, 'message': 'OTP expired. Please login again.'}), 400

    if not check_password_hash(user.otp_code, otp):
        log_action('FAILED_OTP', 'User', email, 'Invalid OTP')
        return jsonify({'success': False, 'message': 'Invalid OTP code'}), 401

    # OTP Verified!
    user.otp_verified = True
    user.otp_code = None
    user.otp_expiry = None
    db.session.commit()

    login_user(user, remember=True)
    log_action('LOGIN_SUCCESS', 'User', user.id)
    return jsonify({'success': True, 'user': user.to_dict()}), 200

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or request.form
    username = (data.get('name') or data.get('username', '')).strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')

    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    if password != confirm:
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
        is_admin=User.query.count() == 0
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    log_action('SIGNUP', 'User', user.id)
    return jsonify({'success': True, 'user': user.to_dict()}), 201

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    log_action('LOGOUT', 'User', current_user.id)
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out'}), 200

@app.route('/api/auth/me', methods=['GET'])
def me():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': current_user.to_dict()}), 200
    return jsonify({'authenticated': False}), 200

# ═══════════════════════════════════════════════
#  STUDENT / CADET  ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/students/enroll', methods=['POST'])
def enroll_student():
    data = request.form
    required = ['first_name', 'last_name', 'dob', 'gender', 'phone', 'email', 'roll_no', 'branch', 'year', 'ncc_wing']
    missing = [f for f in required if not data.get(f, '').strip()]
    if missing:
        return jsonify({'success': False, 'message': f"Missing fields: {', '.join(missing)}"}), 400

    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400
    if not re.match(r"^\+?1?\d{9,15}$", phone):
        return jsonify({'success': False, 'message': 'Invalid phone format'}), 400

    if Student.query.filter_by(roll_no=data['roll_no'].strip()).first():
        return jsonify({'success': False, 'message': 'A student with this roll number is already enrolled'}), 409

    photo_filename = save_upload('photo')

    student = Student(
        first_name=data['first_name'].strip(),
        last_name=data['last_name'].strip(),
        dob=data['dob'].strip(),
        gender=data['gender'].strip(),
        phone=data['phone'].strip(),
        email=data['email'].strip(),
        address=data.get('address', '').strip(),
        roll_no=data['roll_no'].strip(),
        branch=data['branch'].strip(),
        year=data['year'].strip(),
        ncc_wing=data['ncc_wing'].strip(),
        prev_experience=data.get('prev_experience', '').strip(),
        motivation=data.get('motivation', '').strip(),
        photo_path=photo_filename,
    )
    db.session.add(student)
    db.session.commit()
    
    send_enrollment_confirmation(student)

    return jsonify({
        'success': True,
        'message': 'Enrollment submitted! ANO office will contact you within 3-5 days.',
        'student_id': student.id
    }), 201

@app.route('/api/students', methods=['GET'])
@login_required
def get_students():
    status = request.args.get('status')
    branch = request.args.get('branch')
    search = request.args.get('search', '').strip()

    query = Student.query
    if status:
        query = query.filter_by(status=status)
    if branch:
        query = query.filter_by(branch=branch)
    if search:
        like = f'%{search}%'
        query = query.filter(db.or_(
            Student.first_name.ilike(like), Student.last_name.ilike(like),
            Student.roll_no.ilike(like), Student.email.ilike(like)
        ))

    query = query.order_by(Student.enrolled_at.desc())
    res = paginate_query(query)
    return jsonify({'success': True, 'students': res['items'], 'pagination': res['pagination']}), 200

@app.route('/api/students/<int:student_id>', methods=['GET'])
@login_required
def get_student(student_id):
    student = Student.query.get_or_404(student_id)
    return jsonify({'success': True, 'student': student.to_dict()}), 200

@app.route('/api/students/<int:student_id>/status', methods=['PATCH'])
@require_role('admin')
def update_student_status(student_id):
    student = Student.query.get_or_404(student_id)
    data = request.get_json(silent=True) or {}

    new_status = data.get('status')
    if new_status and new_status in ('pending', 'approved', 'rejected'):
        old_status = student.status
        student.status = new_status
        student.cadet_no = data.get('cadet_no', student.cadet_no)
        student.remarks = data.get('remarks', student.remarks)
        db.session.commit()
        
        if old_status != new_status:
            send_status_update(student)
            log_action('UPDATE_STUDENT_STATUS', 'Student', student.id, f"{old_status} -> {new_status}")

        return jsonify({'success': True, 'student': student.to_dict()}), 200
    return jsonify({'success': False, 'message': 'Invalid status'}), 400

@app.route('/api/students/<int:student_id>', methods=['PUT'])
@login_required
def update_student(student_id):
    """Admin full edit of a student profile"""
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    student = Student.query.get_or_404(student_id)
    data = request.form if request.form else request.get_json(silent=True)
    if not data: return jsonify({'success': False, 'message': 'No data provided'}), 400

    fname = save_upload('photo')
    if fname:
        delete_upload(student.photo_path)
        student.photo_path = fname

    # Update all safe fields
    for field in ['first_name','last_name','dob','gender','phone','email','address','branch','year','ncc_wing','cadet_no','remarks']:
        if field in data:
            setattr(student, field, data[field])

    db.session.commit()
    log_action('UPDATE_STUDENT_FULL', 'Student', student.id)
    return jsonify({'success': True, 'student': student.to_dict()}), 200

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    student = Student.query.get_or_404(student_id)
    delete_upload(student.photo_path) # clear photo
    db.session.delete(student)
    db.session.commit()
    log_action('DELETE_STUDENT', 'Student', student_id)
    return jsonify({'success': True, 'message': 'Student deleted'}), 200

# ═══════════════════════════════════════════════
#  BULK EXCEL IMPORT & EXPORT
# ═══════════════════════════════════════════════
@app.route('/api/students/export', methods=['GET'])
@require_role('admin')
def export_students():
    students = Student.query.order_by(Student.enrolled_at.desc()).all()
    try:
        buf = excel_utils.export_students_excel(students)
        return send_file(
            buf, as_attachment=True, download_name=f"NCC_Students_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        return jsonify({'success': False, 'message': 'Export failed'}), 500

@app.route('/api/students/import-template', methods=['GET'])
@require_role('admin')
def get_import_template():
    buf = excel_utils.generate_import_template()
    return send_file(
        buf, as_attachment=True, download_name="NCC_Import_Template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/api/students/bulk-import', methods=['POST'])
@require_role('admin')
def bulk_import_students():
    f = request.files.get('file')
    if not f or not f.filename.endswith('.xlsx'):
        return jsonify({'success': False, 'message': 'Please upload a valid .xlsx file.'}), 400
    
    try:
        parsed_rows = excel_utils.parse_bulk_students(f.stream)
        count = 0
        for data in parsed_rows:
            # skip if already enrolled
            if Student.query.filter_by(roll_no=data['roll_no']).first():
                continue
            
            student = Student(
                roll_no=data['roll_no'], first_name=data['first_name'], last_name=data['last_name'],
                dob=data['dob'], gender=data['gender'], phone=data['phone'], email=data['email'],
                branch=data['branch'], year=data['year'], ncc_wing=data['ncc_wing'],
                prev_experience=data['prev_experience'], address=data['address'], motivation=data['motivation'],
                status='approved'  # bulk imports default to approved
            )
            db.session.add(student)
            count += 1
            
        db.session.commit()
        log_action('BULK_IMPORT', 'Student', details=f"Imported {count} cadets")
        return jsonify({'success': True, 'message': f'Successfully imported {count} new cadets. Existing roll numbers were skipped.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ═══════════════════════════════════════════════
#  QR CODE ATTENDANCE
# ═══════════════════════════════════════════════
@app.route('/api/students/<int:student_id>/qr', methods=['GET'])
@login_required
def get_cadet_qr(student_id):
    student = Student.query.get_or_404(student_id)
    if not current_user.is_admin and getattr(current_user, 'student_id_link', None) != student_id:
        # We need to map logged in user to student to restrict this. We can use student.user_id 
        if getattr(student, 'user_id', None) != current_user.id and current_user.role == 'cadet':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
            
    try:
        buf = qr_utils.generate_cadet_qr(student, app.config['SECRET_KEY'])
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        logger.error(f"QR gen err: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate QR'}), 500

@app.route('/api/attendance/scan', methods=['POST'])
@require_role('admin', 'suo')
def scan_qr_attendance():
    data = request.get_json(silent=True) or {}
    token = data.get('qr_token')
    date_str = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    parade_type = data.get('parade_type', 'Drill')
    
    if not token:
        return jsonify({'success': False, 'message': 'Token missing'}), 400
        
    try:
        payload = qr_utils.validate_qr_token(token, app.config['SECRET_KEY'])
        student_id = payload['id']
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': 'Invalid student in QR'}), 404
            
        # mark present
        att = AttendanceRecord.query.filter_by(student_id=student.id, date=date_str).first()
        if att:
            att.present = True
            att.parade_type = parade_type
        else:
            att = AttendanceRecord(student_id=student.id, date=date_str, parade_type=parade_type, present=True)
            db.session.add(att)
            
        db.session.commit()
        log_action('QR_SCAN', 'Attendance', student.id, f"Marked present on {date_str}")
        
        return jsonify({'success': True, 'message': f"{student.first_name} {student.last_name} marked present."}), 200
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400


# ═══════════════════════════════════════════════
#  PDF CERTIFICATES
# ═══════════════════════════════════════════════
@app.route('/api/students/<int:student_id>/certificate', methods=['GET'])
@login_required
def download_certificate(student_id):
    student = Student.query.get_or_404(student_id)
    # Admins can download anyone's cert; cadets can only download their own
    if not current_user.is_admin:
        cadet_profile = Student.query.filter_by(user_id=current_user.id).first()
        if not cadet_profile or cadet_profile.id != student_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    if student.status != 'approved':
        return jsonify({'success': False, 'message': 'Only approved cadets can get certificates'}), 400
        
    try:
        cert_file = generate_enrollment_certificate(student, app.config['CERT_FOLDER'])
        
        # Track the cert in DB
        if not Certificate.query.filter_by(student_id=student.id, cert_type='Enrollment').first():
            cert = Certificate(student_id=student.id, cert_type='Enrollment', file_path=cert_file)
            db.session.add(cert)
            db.session.commit()
            log_action('GENERATE_CERTIFICATE', 'Student', student.id)

        return send_file(os.path.join(app.config['CERT_FOLDER'], cert_file), as_attachment=True)
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate certificate'}), 500

# ═══════════════════════════════════════════════
#  NOTICE BOARD  ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/notices', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_notices():
    category = request.args.get('category')
    query = Notice.query
    if category:
        query = query.filter_by(category=category)
    query = query.order_by(Notice.created_at.desc())
    res = paginate_query(query)
    return jsonify({'success': True, 'notices': res['items'], 'pagination': res['pagination']}), 200

@app.route('/api/notices', methods=['POST'])
@login_required
def create_notice():
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    data = request.form
    if not data.get('title') or not data.get('category') or not data.get('description'):
        return jsonify({'success': False, 'message': 'title, category and description required'}), 400

    notice = Notice(
        title=data['title'], category=data['category'],
        description=data['description'], issued_by=data.get('issued_by', 'ANO Office'),
        file_path=save_upload('file')
    )
    db.session.add(notice)
    db.session.commit()
    log_action('CREATE_NOTICE', 'Notice', notice.id)
    return jsonify({'success': True, 'notice': notice.to_dict()}), 201

@app.route('/api/notices/<int:notice_id>', methods=['PATCH'])
@login_required
def update_notice(notice_id):
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    notice = Notice.query.get_or_404(notice_id)
    data = request.form if request.form else request.get_json(silent=True)
    
    if 'title' in data: notice.title = data['title']
    if 'category' in data: notice.category = data['category']
    if 'description' in data: notice.description = data['description']
    
    fpath = save_upload('file')
    if fpath:
        delete_upload(notice.file_path)
        notice.file_path = fpath
        
    db.session.commit()
    log_action('UPDATE_NOTICE', 'Notice', notice.id)
    return jsonify({'success': True, 'notice': notice.to_dict()}), 200

@app.route('/api/notices/<int:notice_id>', methods=['DELETE'])
@login_required
def delete_notice(notice_id):
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    notice = Notice.query.get_or_404(notice_id)
    delete_upload(notice.file_path)
    db.session.delete(notice)
    db.session.commit()
    log_action('DELETE_NOTICE', 'Notice', notice_id)
    return jsonify({'success': True, 'message': 'Notice deleted'}), 200

# ═══════════════════════════════════════════════
#  GALLERY  ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    category = request.args.get('category')
    query = GalleryItem.query
    if category: query = query.filter_by(category=category)
    query = query.order_by(GalleryItem.uploaded_at.desc())
    res = paginate_query(query)
    return jsonify({'success': True, 'gallery': res['items'], 'pagination': res['pagination']}), 200

@app.route('/api/gallery', methods=['POST'])
@login_required
def add_gallery_item():
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    data = request.form
    img = save_upload('image')
    if not img: return jsonify({'success': False, 'message': 'Image required'}), 400

    item = GalleryItem(title=data.get('title',''), category=data.get('category',''), description=data.get('description',''), image_path=img)
    db.session.add(item)
    db.session.commit()
    log_action('CREATE_GALLERY', 'GalleryItem', item.id)
    return jsonify({'success': True, 'item': item.to_dict()}), 201

@app.route('/api/gallery/<int:item_id>', methods=['PUT', 'PATCH'])
@login_required
def update_gallery(item_id):
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    item = GalleryItem.query.get_or_404(item_id)
    data = request.form if request.form else request.get_json(silent=True)
    
    if 'title' in data: item.title = data['title']
    if 'category' in data: item.category = data['category']
    if 'description' in data: item.description = data['description']
    
    img = save_upload('image')
    if img:
        delete_upload(item.image_path)
        item.image_path = img
        
    db.session.commit()
    log_action('UPDATE_GALLERY', 'GalleryItem', item.id)
    return jsonify({'success': True, 'item': item.to_dict()}), 200

@app.route('/api/gallery/<int:item_id>', methods=['DELETE'])
@login_required
def delete_gallery_item(item_id):
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    item = GalleryItem.query.get_or_404(item_id)
    delete_upload(item.image_path)
    db.session.delete(item)
    db.session.commit()
    log_action('DELETE_GALLERY', 'GalleryItem', item_id)
    return jsonify({'success': True, 'message': 'Item deleted'}), 200

# ═══════════════════════════════════════════════
#  CAMPS & REGISTRATION ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/camps', methods=['GET'])
def get_camps():
    camps = Camp.query.order_by(Camp.start_date.desc()).all()
    return jsonify({'success': True, 'camps': [c.to_dict() for c in camps]}), 200

@app.route('/api/camps', methods=['POST'])
@login_required
def create_camp():
    if not current_user.is_admin: return jsonify({'success': False, 'message': 'Admin access needed'}), 403
    data = request.get_json(silent=True) or request.form
    camp = Camp(
        name=data.get('name',''), location=data.get('location',''), camp_type=data.get('camp_type',''),
        start_date=data.get('start_date',''), end_date=data.get('end_date',''), description=data.get('description',''),
        is_upcoming=data.get('is_upcoming', True), capacity=data.get('capacity', 50)
    )
    db.session.add(camp)
    db.session.commit()
    log_action('CREATE_CAMP', 'Camp', camp.id)
    return jsonify({'success': True, 'camp': camp.to_dict()}), 201

@app.route('/api/camps/<int:camp_id>', methods=['PUT', 'PATCH'])
@login_required
def update_camp(camp_id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    camp = Camp.query.get_or_404(camp_id)
    data = request.get_json(silent=True) or request.form
    for field in ['name','location','camp_type','start_date','end_date','description','is_upcoming','capacity']:
        if field in data:
            setattr(camp, field, data[field])
    db.session.commit()
    log_action('UPDATE_CAMP', 'Camp', camp.id)
    return jsonify({'success': True, 'camp': camp.to_dict()}), 200

@app.route('/api/camps/<int:camp_id>', methods=['DELETE'])
@login_required
def delete_camp(camp_id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    camp = Camp.query.get_or_404(camp_id)
    db.session.delete(camp)
    db.session.commit()
    log_action('DELETE_CAMP', 'Camp', camp_id)
    return jsonify({'success': True, 'message': 'Camp deleted'}), 200

@app.route('/api/camps/<int:camp_id>/register', methods=['POST'])
def register_camp(camp_id):
    # Public route: Cadet enters roll no to register
    data = request.get_json(silent=True) or request.form
    roll_no = data.get('roll_no')
    if not roll_no: return jsonify({'success': False, 'message': 'Roll Number required'}), 400
    
    student = Student.query.filter_by(roll_no=roll_no).first()
    if not student or student.status != 'approved':
        return jsonify({'success': False, 'message': 'Only approved cadets can register'}), 400
        
    camp = Camp.query.get_or_404(camp_id)
    if not camp.is_upcoming:
        return jsonify({'success': False, 'message': 'Camp registration closed'}), 400
        
    if camp.registered_count >= camp.capacity:
        return jsonify({'success': False, 'message': 'Camp is full'}), 400
        
    reg = CampRegistration.query.filter_by(camp_id=camp.id, student_id=student.id).first()
    if reg:
        return jsonify({'success': False, 'message': 'Already registered'}), 409
        
    new_reg = CampRegistration(camp_id=camp.id, student_id=student.id)
    db.session.add(new_reg)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Camp registration successful'}), 201

@app.route('/api/camps/<int:camp_id>/registrations/<int:reg_id>', methods=['PATCH'])
@login_required
def update_camp_registration(camp_id, reg_id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    reg = CampRegistration.query.get_or_404(reg_id)
    if reg.camp_id != camp_id: return jsonify({'success': False, 'message': 'Mismatch'}), 400
    data = request.get_json(silent=True) or {}
    if 'status' in data and data['status'] in ('registered', 'accepted', 'rejected', 'cancelled'):
        reg.status = data['status']
        db.session.commit()
        log_action('UPDATE_CAMP_REG', 'CampRegistration', reg_id, f"Status: {reg.status}")
        return jsonify({'success': True, 'registration': reg.to_dict()}), 200
    return jsonify({'success': False, 'message': 'Invalid status'}), 400

# ═══════════════════════════════════════════════
#  ACHIEVEMENTS  ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/achievements', methods=['GET'])
def get_achievements():
    achievements = Achievement.query.order_by(Achievement.year.desc()).all()
    return jsonify({'success': True, 'achievements': [a.to_dict() for a in achievements]}), 200

@app.route('/api/achievements', methods=['POST'])
@login_required
def create_achievement():
    if not current_user.is_admin: return jsonify({'success': False}), 403
    data = request.form
    ach = Achievement(
        cadet_name=data.get('cadet_name',''), title=data.get('title',''), description=data.get('description',''),
        year=int(data.get('year', 2024)), level=data.get('level','State'), image_path=save_upload('image')
    )
    db.session.add(ach)
    db.session.commit()
    log_action('CREATE_ACH', 'Achievement', ach.id)
    return jsonify({'success': True, 'achievement': ach.to_dict()}), 201

@app.route('/api/achievements/<int:id>', methods=['PUT', 'PATCH'])
@login_required
def update_achievement(id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    ach = Achievement.query.get_or_404(id)
    data = request.form if request.form else request.get_json(silent=True)
    
    for field in ['cadet_name','title','description','year','level']:
        if field in data:
            setattr(ach, field, data[field] if field!='year' else int(data[field]))
            
    img = save_upload('image')
    if img:
        delete_upload(ach.image_path)
        ach.image_path = img
        
    db.session.commit()
    log_action('UPDATE_ACH', 'Achievement', ach.id)
    return jsonify({'success': True, 'achievement': ach.to_dict()}), 200

@app.route('/api/achievements/<int:id>', methods=['DELETE'])
@login_required
def delete_achievement(id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    ach = Achievement.query.get_or_404(id)
    delete_upload(ach.image_path)
    db.session.delete(ach)
    db.session.commit()
    log_action('DELETE_ACH', 'Achievement', id)
    return jsonify({'success': True, 'message': 'Deleted'}), 200

# ═══════════════════════════════════════════════
#  ATTENDANCE ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/attendance', methods=['POST'])
@login_required
def mark_attendance():
    """Batch mark attendance: {date, parade_type, records: [{student_id, present}]}"""
    if not current_user.is_admin: return jsonify({'success': False}), 403
    data = request.get_json(silent=True) or {}
    date = data.get('date')
    parade_type = data.get('parade_type')
    records = data.get('records', [])
    
    if not date or not parade_type or not records:
        return jsonify({'success': False, 'message': 'Missing date, type or records'}), 400
        
    count = 0
    for r in records:
        sid = r.get('student_id')
        att = AttendanceRecord.query.filter_by(student_id=sid, date=date).first()
        if not att:
            att = AttendanceRecord(student_id=sid, date=date, parade_type=parade_type, present=r.get('present', False))
            db.session.add(att)
        else:
            att.present = r.get('present', False)
            att.parade_type = parade_type
        count += 1
        
    db.session.commit()
    log_action('MARK_ATTENDANCE', 'Attendance', None, f'Marked {count} records for {date}')
    return jsonify({'success': True, 'message': f'Marked {count} records'}), 201

@app.route('/api/attendance', methods=['GET'])
@login_required
def get_attendance():
    date = request.args.get('date')
    student_id = request.args.get('student_id')
    query = AttendanceRecord.query
    if date: query = query.filter_by(date=date)
    if student_id: query = query.filter_by(student_id=student_id)
    query = query.order_by(AttendanceRecord.date.desc())
    res = paginate_query(query)
    return jsonify({'success': True, 'attendance': res['items'], 'pagination': res['pagination']}), 200

@app.route('/api/attendance/summary', methods=['GET'])
@login_required
def get_attendance_summary():
    if not current_user.is_admin: return jsonify({'success': False}), 403
    from sqlalchemy import func
    
    # Returns percentage for each student overall
    totals = db.session.query(
        AttendanceRecord.student_id, func.count(AttendanceRecord.id)
    ).group_by(AttendanceRecord.student_id).all()
    totals_dict = {t[0]: t[1] for t in totals}
    
    presents = db.session.query(
        AttendanceRecord.student_id, func.count(AttendanceRecord.id)
    ).filter_by(present=True).group_by(AttendanceRecord.student_id).all()
    presents_dict = {p[0]: p[1] for p in presents}
    
    students = Student.query.filter_by(status='approved').all()
    summary = []
    for s in students:
        total = totals_dict.get(s.id, 0)
        present = presents_dict.get(s.id, 0)
        perc = (present / total * 100) if total > 0 else 0
        summary.append({'student_id': s.id, 'roll_no': s.roll_no, 'name': s.first_name, 'total': total, 'present': present, 'percentage': round(perc, 1)})
    return jsonify({'success': True, 'summary': summary}), 200

@app.route('/api/attendance/export', methods=['GET'])
@require_role('admin')
def export_attendance():
    date = request.args.get('date')
    query = AttendanceRecord.query.order_by(AttendanceRecord.date.desc())
    if date:
        query = query.filter_by(date=date)
    records = query.all()
    try:
        buf = excel_utils.export_attendance_excel(records)
        return send_file(
            buf, as_attachment=True, download_name=f"Attendance_{date or 'All'}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Attendance export error: {e}")
        return jsonify({'success': False, 'message': 'Export failed'}), 500

# ═══════════════════════════════════════════════
#  CONTACT  ROUTES
# ═══════════════════════════════════════════════
@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json(silent=True) or request.form
    if not data.get('name') or not data.get('email') or not data.get('message'):
        return jsonify({'success': False, 'message': 'Name, email and message are required'}), 400

    msg = ContactMessage(
        name=data['name'], email=data['email'], phone=data.get('phone', ''),
        subject=data.get('subject', 'General Inquiry'), message=data['message']
    )
    db.session.add(msg)
    db.session.commit()
    send_contact_autoreply(msg)
    return jsonify({'success': True, 'message': 'Your message has been received.'}), 201

@app.route('/api/contact', methods=['GET'])
@login_required
def get_contact_messages():
    if not current_user.is_admin: return jsonify({'success': False}), 403
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return jsonify({'success': True, 'messages': [m.to_dict() for m in msgs]}), 200

@app.route('/api/contact/<int:id>/read', methods=['PATCH'])
@login_required
def mark_contact_read(id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'message': msg.to_dict()}), 200

@app.route('/api/contact/<int:id>', methods=['DELETE'])
@login_required
def delete_contact(id):
    if not current_user.is_admin: return jsonify({'success': False}), 403
    msg = ContactMessage.query.get_or_404(id)
    db.session.delete(msg)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200

# ═══════════════════════════════════════════════
#  AUDIT LOG ROUTE
# ═══════════════════════════════════════════════
@app.route('/api/audit-log', methods=['GET'])
@login_required
def get_audit_log():
    if not current_user.is_admin: return jsonify({'success': False}), 403
    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    res = paginate_query(query)
    return jsonify({'success': True, 'logs': res['items'], 'pagination': res['pagination']}), 200

# ═══════════════════════════════════════════════
#  CADET PORTAL (Self-Service)
# ═══════════════════════════════════════════════
@app.route('/api/cadet/profile', methods=['GET'])
def cadet_profile():
    if current_user.is_authenticated and not current_user.is_admin:
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student: return jsonify({'success': False, 'message': 'Profile not found'}), 404
    else:
        roll_no = request.args.get('roll_no')
        dob = request.args.get('dob')
        if not roll_no or not dob: return jsonify({'success': False, 'message': 'Roll Number and DOB required'}), 400
        student = Student.query.filter_by(roll_no=roll_no).first()
        if not student or student.dob != dob: return jsonify({'success': False, 'message': 'Invalid credentials'}), 404
    
    total = AttendanceRecord.query.filter_by(student_id=student.id).count()
    present = AttendanceRecord.query.filter_by(student_id=student.id, present=True).count()
    attendance_perc = (present / total * 100) if total > 0 else 0
    
    return jsonify({
        'success': True, 
        'student': student.to_dict(),
        'attendance_summary': {'total': total, 'present': present, 'percentage': round(attendance_perc, 1)}
    }), 200

@app.route('/api/cadet/camps', methods=['GET'])
@login_required
def cadet_camps():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    
    regs = CampRegistration.query.filter_by(student_id=student.id).all()
    data = []
    for r in regs:
        camp_dict = r.camp.to_dict() if r.camp else {}
        data.append({
            'registration_id': r.id,
            'status': r.status,
            'applied_on': r.registered_at.isoformat() if r.registered_at else None,
            'camp': camp_dict
        })
    return jsonify({'success': True, 'camps': data}), 200

# ═══════════════════════════════════════════════
#  CADET SELF-SERVICE NEW APIS
# ═══════════════════════════════════════════════
@app.route('/api/cadet/profile', methods=['PUT'])
@login_required
def update_cadet_profile():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    data = request.get_json(silent=True) or request.form
    if 'phone' in data: student.phone = data['phone']
    if 'address' in data: student.address = data['address']
    db.session.commit()
    return jsonify({'success': True, 'student': student.to_dict()}), 200

@app.route('/api/cadet/documents', methods=['GET'])
@login_required
def get_cadet_documents():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    docs = Document.query.filter_by(student_id=student.id).order_by(Document.uploaded_at.desc()).all()
    return jsonify({'success': True, 'documents': [d.to_dict() for d in docs]}), 200

@app.route('/api/cadet/documents', methods=['POST'])
@login_required
def upload_cadet_document():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    doc_type = request.form.get('doc_type')
    if not doc_type: return jsonify({'success': False, 'message': 'Document type required'}), 400
    fname = save_upload('file')
    if not fname: return jsonify({'success': False, 'message': 'File upload failed'}), 400
    doc = Document(student_id=student.id, doc_type=doc_type, file_path=fname)
    db.session.add(doc)
    db.session.commit()
    return jsonify({'success': True, 'document': doc.to_dict()}), 201

@app.route('/api/cadet/queries', methods=['GET'])
@login_required
def get_cadet_queries():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    queries = HelpdeskQuery.query.filter_by(student_id=student.id).order_by(HelpdeskQuery.created_at.desc()).all()
    return jsonify({'success': True, 'queries': [q.to_dict() for q in queries]}), 200

@app.route('/api/cadet/queries', methods=['POST'])
@login_required
def submit_cadet_query():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    data = request.get_json(silent=True) or request.form
    subject = data.get('subject')
    message = data.get('message')
    if not subject or not message: return jsonify({'success': False, 'message': 'Subject and message are required'}), 400
    query = HelpdeskQuery(student_id=student.id, subject=subject, message=message)
    db.session.add(query)
    db.session.commit()
    return jsonify({'success': True, 'query': query.to_dict()}), 201

@app.route('/api/cadet/upcoming', methods=['GET'])
@login_required
def get_cadet_upcoming():
    if current_user.is_admin: return jsonify({'success': False}), 403
    upcoming_camps = Camp.query.filter_by(is_upcoming=True).order_by(Camp.start_date.asc()).limit(3).all()
    recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(3).all()
    return jsonify({'success': True, 'camps': [c.to_dict() for c in upcoming_camps], 'notices': [n.to_dict() for n in recent_notices]}), 200

@app.route('/api/cadet/badges', methods=['GET'])
@login_required
def get_cadet_badges():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    
    badges = []
    # Badge logic based on dynamic data
    if student.status == 'approved':
        badges.append({'title': 'Verified Cadet', 'icon': 'fa-check-circle', 'color': 'text-green-500', 'desc': 'Successfully enrolled.'})
    
    total = AttendanceRecord.query.filter_by(student_id=student.id).count()
    present = AttendanceRecord.query.filter_by(student_id=student.id, present=True).count()
    if total > 0 and (present / total) >= 0.8:
        badges.append({'title': 'Regular Attendee', 'icon': 'fa-calendar-check', 'color': 'text-blue-500', 'desc': 'Above 80% attendance.'})
        
    camp_count = CampRegistration.query.filter_by(student_id=student.id, status='accepted').count()
    if camp_count > 0:
        badges.append({'title': 'Camper', 'icon': 'fa-tent', 'color': 'text-yellow-500', 'desc': 'Attended at least one camp.'})

    return jsonify({'success': True, 'badges': badges}), 200

@app.route('/api/cadet/attendance/trends', methods=['GET'])
@login_required
def get_cadet_attendance_trends():
    if current_user.is_admin: return jsonify({'success': False}), 403
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student: return jsonify({'success': False}), 404
    
    # Simple logic: group all attendance dates by YYYY-MM
    records = AttendanceRecord.query.filter_by(student_id=student.id).all()
    trend_dict = {}
    for r in records:
        if not r.date: continue
        month = r.date[:7] # e.g. '2023-11'
        if month not in trend_dict: trend_dict[month] = {'present': 0, 'total': 0}
        trend_dict[month]['total'] += 1
        if r.present: trend_dict[month]['present'] += 1
        
    labels = sorted(trend_dict.keys())
    data = []
    for lbl in labels:
        data.append(trend_dict[lbl]['present'] / trend_dict[lbl]['total'] * 100)
        
    return jsonify({'success': True, 'labels': labels, 'data': data}), 200

# ═══════════════════════════════════════════════
#  GAMIFICATION / LEADERBOARD
# ═══════════════════════════════════════════════
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Public leaderboard route."""
    from sqlalchemy import func
    # Get sum of points per cadet
    scores = db.session.query(
        CadetPoints.student_id, func.sum(CadetPoints.points).label('total')
    ).group_by(CadetPoints.student_id).order_by(db.text('total DESC')).limit(10).all()

    leaderboard = []
    for s_id, total in scores:
        student = Student.query.get(s_id)
        if student:
            leaderboard.append({
                'student_id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'roll_no': student.roll_no,
                'points': total,
                'photo_url': f'/uploads/{student.photo_path}' if student.photo_path else None
            })
    return jsonify({'success': True, 'leaderboard': leaderboard}), 200

@app.route('/api/leaderboard/award', methods=['POST'])
@require_role('admin', 'suo')
def award_points():
    data = request.get_json(silent=True) or request.form
    student_id = data.get('student_id')
    points = data.get('points')
    reason = data.get('reason')
    
    if not student_id or not points or not reason:
        return jsonify({'success': False, 'message': 'Required details missing'}), 400
        
    try:
        points = int(points)
        pt = CadetPoints(student_id=student_id, points=points, reason=reason, awarded_by=current_user.id)
        db.session.add(pt)
        db.session.commit()
        log_action('AWARD_POINTS', 'CadetPoints', pt.id, f"Awarded {points} to student {student_id}")
        return jsonify({'success': True, 'message': 'Points awarded successfully'}), 201
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid points value'}), 400

# ═══════════════════════════════════════════════
#  STUDY MATERIAL HUB
# ═══════════════════════════════════════════════
@app.route('/api/study-materials', methods=['GET'])
@login_required
def get_study_materials():
    category = request.args.get('category')
    query = StudyMaterial.query
    if category:
        query = query.filter_by(category=category)
    materials = query.order_by(StudyMaterial.uploaded_at.desc()).all()
    return jsonify({'success': True, 'materials': [m.to_dict() for m in materials]}), 200

@app.route('/api/study-materials', methods=['POST'])
@require_role('admin', 'suo')
def upload_study_material():
    data = request.form
    title = data.get('title')
    category = data.get('category')
    
    if not title or not category:
        return jsonify({'success': False, 'message': 'Title and category required'}), 400
        
    fname = save_upload('file')
    if not fname:
        return jsonify({'success': False, 'message': 'File upload failed or invalid format'}), 400
        
    mat = StudyMaterial(title=title, category=category, description=data.get('description', ''), file_path=fname, uploaded_by=current_user.id)
    db.session.add(mat)
    db.session.commit()
    log_action('UPLOAD_STUDENT_MATERIAL', 'StudyMaterial', mat.id, f"{title}")
    return jsonify({'success': True, 'material': mat.to_dict()}), 201

@app.route('/api/study-materials/<int:mat_id>', methods=['DELETE'])
@require_role('admin')
def delete_study_material(mat_id):
    mat = StudyMaterial.query.get_or_404(mat_id)
    delete_upload(mat.file_path)
    db.session.delete(mat)
    db.session.commit()
    log_action('DELETE_STUDENT_MATERIAL', 'StudyMaterial', mat_id)
    return jsonify({'success': True, 'message': 'Deleted successfully'}), 200

# ═══════════════════════════════════════════════
#  HELPDESK (ADMIN ROUTES)
# ═══════════════════════════════════════════════
@app.route('/api/helpdesk', methods=['GET'])
@require_role('admin')
def admin_get_helpdesk_queries():
    status = request.args.get('status')
    query = HelpdeskQuery.query
    if status:
        query = query.filter_by(status=status)
    queries = query.order_by(HelpdeskQuery.created_at.desc()).all()
    return jsonify({'success': True, 'queries': [q.to_dict() for q in queries]}), 200

@app.route('/api/helpdesk/<int:query_id>', methods=['PATCH'])
@require_role('admin')
def admin_respond_helpdesk(query_id):
    q = HelpdeskQuery.query.get_or_404(query_id)
    data = request.get_json(silent=True) or request.form
    
    if 'status' in data: q.status = data['status']
    if 'response' in data: q.response = data['response']
    
    db.session.commit()
    return jsonify({'success': True, 'query': q.to_dict()}), 200

# ═══════════════════════════════════════════════
#  DASHBOARD STATS
# ═══════════════════════════════════════════════
@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    if not current_user.is_admin: return jsonify({'success': False}), 403

    # breakdown
    wings = db.session.query(Student.ncc_wing, db.func.count(Student.id)).group_by(Student.ncc_wing).all()
    branches = db.session.query(Student.branch, db.func.count(Student.id)).group_by(Student.branch).all()
    
    # recent logs
    recent_logs = [l.to_dict() for l in AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()]

    return jsonify({
        'success': True,
        'stats': {
            'total_students':      Student.query.count(),
            'pending_enrollments': Student.query.filter_by(status='pending').count(),
            'approved_cadets':     Student.query.filter_by(status='approved').count(),
            'total_notices':       Notice.query.count(),
            'total_camps':         Camp.query.count(),
            'unread_messages':     ContactMessage.query.filter_by(is_read=False).count(),
        },
        'wing_breakdown': dict(wings),
        'branch_breakdown': dict(branches),
        'recent_activity': recent_logs
    }), 200

# ─────────────────────────────
#  Init DB + Run
# ─────────────────────────────
if __name__ == '__main__':
    print('🚀 NCC Backend API -> http://127.0.0.1:5000')
    app.run(debug=app.config['DEBUG'], port=5000, host='0.0.0.0')
