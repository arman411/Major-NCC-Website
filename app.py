from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import date, datetime, timedelta
from calendar import monthrange

from models import db, User, Notice, GalleryItem, Attendance, AttendanceRequest, Event, Contact, Achievement

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_override_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ncc_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('images', 'uploads')

# Initialize DB
db.init_app(app)

# Setup Login Manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': True, 'message': 'Session expired or unauthorized. Please login again.', 'status': 401}), 401
    return redirect(url_for('login', next=request.path))

# Create DB Tables on Startup
with app.app_context():
    db.create_all()

# --- Serve root-level asset folders (css, js, images) ---
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('js', filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('.', 'sw.js')

@app.route('/googlef6cddc47ed70c3d7.html')
def serve_google_verification():
    return send_from_directory('.', 'googlef6cddc47ed70c3d7.html')

@app.route('/sitemap.xml')
def serve_sitemap():
    return send_from_directory('.', 'sitemap.xml')

@app.route('/robots.txt')
def serve_robots():
    return send_from_directory('.', 'robots.txt')

# --- Health Check (for UptimeRobot and internal sync) ---
@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'message': 'NCC GPH Hamirpur server is running'})

# --- API Logout Route ---
@app.route('/api/auth/logout', methods=['POST', 'GET'])
def api_auth_logout():
    logout_user()
    return jsonify({'error': False, 'message': 'Logged out successfully'})

# --- One-time Admin Setup for Render (visit once, then it auto-disables) ---
@app.route('/setup-admin')
def setup_admin():
    existing = User.query.filter_by(email='admin@ncc-gph.ac.in').first()
    if existing:
        return jsonify({'message': 'Admin already exists. Login with admin@ncc-gph.ac.in and NCC@Admin2025'})
    admin = User(
        username='admin',
        email='admin@ncc-gph.ac.in',
        password_hash=generate_password_hash('NCC@Admin2025', method='pbkdf2:sha256'),
        is_admin=True,
        is_approved=True
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({'message': 'Admin created successfully! Email: admin@ncc-gph.ac.in | Password: NCC@Admin2025'})

# --- Catch-all for /pages/<name>.html links (from static site) ---
@app.route('/pages/<path:filename>')
def serve_page(filename):
    template_name = filename if filename.endswith('.html') else filename + '.html'
    return render_template(template_name)

# --- Public Routes ---

@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/unit')
def unit():
    return render_template('unit.html')

@app.route('/activities')
def activities():
    return render_template('activities.html')

@app.route('/gallery')
def gallery():
    images = GalleryItem.query.order_by(GalleryItem.uploaded_at.desc()).all()
    return render_template('gallery.html', images=images)

@app.route('/achievements')
def achievements():
    return render_template('achievements.html')

@app.route('/notices')
def notices():
    all_notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return render_template('notices.html', notices=all_notices)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/enrollment')
def enrollment():
    return render_template('enrollment.html')

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('name') or request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'error')
            return redirect(url_for('signup'))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    data = request.get_json(force=True) or {}
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    phone_number = data.get('phone_number', '').strip()
    roll_no = data.get('roll_no', '')
    branch = data.get('branch', '')
    year = data.get('year', '')

    if not email or not username or not password:
        return jsonify({'error': True, 'message': 'Missing required fields'}), 400

    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        return jsonify({'error': True, 'message': 'Email or Username already exists'}), 400

    new_user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        is_admin=False,
        is_approved=False,
        roll_no=roll_no,
        branch=branch,
        year=year
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'error': False, 'message': 'Registered successfully'})

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.get_json(force=True) or {}
    username_or_email = data.get('username', '').strip() or data.get('email', '').strip()
    password = data.get('password', '')

    user = User.query.filter((User.email == username_or_email.lower()) | (User.username == username_or_email)).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user, remember=True)
        return jsonify({
            'error': False, 
            'message': 'Login successful', 
            'is_admin': user.is_admin,
            'access_token': 'flask_backend_session_active',
            'user': {
                'username': user.username,
                'email': user.email,
                'role': 'admin' if user.is_admin else 'cadet'
            }
        })
    return jsonify({'error': True, 'message': 'Invalid credentials'}), 401

@app.route('/api/cadet/settings', methods=['GET'])
@login_required
def get_cadet_settings():
    if current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin does not have cadet settings'}), 400
    
    return jsonify({
        'error': False,
        'settings': {
            'username': current_user.username,
            'email': current_user.email,
            'first_name': current_user.first_name or '',
            'last_name': current_user.last_name or '',
            'phone_number': current_user.phone_number or '',
            'roll_no': current_user.roll_no or '',
            'branch': current_user.branch or '',
            'year': current_user.year or '',
            'theme_preference': current_user.theme_preference or 'system'
        }
    })

@app.route('/api/cadet/settings', methods=['PUT'])
@login_required
def update_cadet_settings():
    if current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin does not have cadet settings'}), 400

    data = request.get_json(force=True) or {}
    
    # Update fields if provided
    if 'first_name' in data: current_user.first_name = data['first_name'].strip()
    if 'last_name' in data: current_user.last_name = data['last_name'].strip()
    if 'phone_number' in data: current_user.phone_number = data['phone_number'].strip()
    if 'branch' in data: current_user.branch = data['branch'].strip()
    if 'year' in data: current_user.year = data['year'].strip()
    if 'theme_preference' in data: current_user.theme_preference = data['theme_preference'].strip()

    # Note: Roll Number, Email, and Username are typically read-only or handled via separate secure processes.
    db.session.commit()
    return jsonify({'error': False, 'message': 'Settings updated successfully'})

@app.route('/api/certificates/mine', methods=['GET'])
@login_required
def api_certificates_mine():
    if current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin does not have certificates'}), 400

    status = 'approved' if current_user.is_approved else 'pending'
    return jsonify({
        'error': False,
        'success': True,
        'status': status,
        'student_id': 'STU-' + current_user.username.upper(),
        'certificates': [
            { 'type': 'A Certificate', 'available': current_user.is_approved, 'download_url': '/api/certificates/download/A' if current_user.is_approved else None },
            { 'type': 'B Certificate', 'available': current_user.is_approved, 'download_url': '/api/certificates/download/B' if current_user.is_approved else None },
        ]
    })

@app.route('/api/certificates/download/<string:cert_type>', methods=['GET'])
@login_required
def api_certificates_download(cert_type):
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    if not current_user.is_approved:
        flash("Your certificate is pending admin enrollment approval.")
        return redirect('/pages/cadet-portal.html')
    
    cert_label = f"{cert_type} Certificate"
    return render_template('certificate.html', user=current_user, cert_type=cert_label)

# --- Protected Routes ---

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        total_cadets = User.query.filter_by(is_admin=False).count()
        total_notices = Notice.query.count()
        recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()

        today = date.today()
        present_today = Attendance.query.filter_by(date=today, status='present').count()
        attendance_pct = round((present_today / total_cadets * 100) if total_cadets > 0 else 0)

        pending_requests = AttendanceRequest.query.filter_by(date=today).count()

        return render_template('admin-dashboard.html',
                               cadet_count=total_cadets,
                               notice_count=total_notices,
                               recent_notices=recent_notices,
                               present_today=present_today,
                               attendance_pct=attendance_pct,
                               pending_requests=pending_requests)
    else:
        return redirect(url_for('index'))

# =============================================================================
# ATTENDANCE API — CADET SIDE
# =============================================================================

@app.route('/api/attendance/request', methods=['POST'])
def api_attendance_request():
    """Cadet submits attendance request for today (requires login or email)."""
    data = request.get_json(force=True) or {}
    today = date.today()

    # Support both logged-in session and email-based lookup
    if current_user.is_authenticated and not current_user.is_admin:
        cadet = current_user
    else:
        email = data.get('email', '').strip().lower()
        if not email:
            return jsonify({'error': True, 'message': 'Email is required'}), 400
        cadet = User.query.filter(
            (db.func.lower(User.email) == email) | (db.func.lower(User.username) == email),
            User.is_admin == False
        ).first()
        if not cadet:
            return jsonify({'error': True, 'message': 'Cadet not found. Please register first.'}), 404

    if not cadet.is_approved:
        return jsonify({'error': True, 'message': 'Account pending admin approval. Cannot mark attendance.'}), 403

    # Check if already requested
    existing_req = AttendanceRequest.query.filter_by(cadet_id=cadet.id, date=today).first()
    if existing_req:
        return jsonify({
            'error': False,
            'already_requested': True,
            'message': f'Attendance request already submitted for {today.strftime("%d %b %Y")}',
            'requested_at': existing_req.requested_at.strftime('%I:%M %p')
        }), 200

    # Check if attendance already finalized by admin
    existing_att = Attendance.query.filter_by(cadet_id=cadet.id, date=today).first()
    if existing_att:
        return jsonify({
            'error': False,
            'already_finalized': True,
            'message': f'Attendance already finalized for today. Status: {existing_att.status}',
            'status': existing_att.status
        }), 200

    note = data.get('note', '')
    req = AttendanceRequest(cadet_id=cadet.id, date=today, note=note)
    db.session.add(req)
    db.session.commit()

    return jsonify({
        'error': False,
        'already_requested': False,
        'message': f'Attendance request submitted for {today.strftime("%d %b %Y")}! Waiting for admin confirmation.',
        'requested_at': req.requested_at.strftime('%I:%M %p')
    }), 200


@app.route('/api/attendance/my-status', methods=['GET'])
def api_my_attendance_status():
    """Cadet: get today's status + full history."""
    if current_user.is_authenticated and not current_user.is_admin:
        cadet = current_user
    else:
        email = request.args.get('email', '').strip().lower()
        if not email:
            return jsonify({'error': True, 'message': 'Email required'}), 400
        cadet = User.query.filter(
            (db.func.lower(User.email) == email) | (db.func.lower(User.username) == email),
            User.is_admin == False
        ).first()
        if not cadet:
            return jsonify({'error': True, 'message': 'Cadet not found'}), 404

    today = date.today()
    today_req = AttendanceRequest.query.filter_by(cadet_id=cadet.id, date=today).first()
    today_att = Attendance.query.filter_by(cadet_id=cadet.id, date=today).first()

    records = Attendance.query.filter_by(cadet_id=cadet.id).order_by(Attendance.date.desc()).all()
    total = len(records)
    present = sum(1 for r in records if r.status == 'present')

    return jsonify({
        'error': False,
        'cadet_name': cadet.username,
        'is_approved': cadet.is_approved,
        'today': today.strftime('%Y-%m-%d'),
        'today_requested': today_req is not None,
        'today_requested_at': today_req.requested_at.strftime('%I:%M %p') if today_req else None,
        'today_finalized': today_att is not None,
        'today_status': today_att.status if today_att else None,
        'total_days': total,
        'present': present,
        'absent': total - present,
        'percentage': round((present / total * 100) if total > 0 else 0),
        'records': [r.to_dict() for r in records]
    })

# =============================================================================
# ATTENDANCE API — ADMIN SIDE
# =============================================================================

@app.route('/api/attendance/daily', methods=['GET'])
def api_attendance_daily():
    """Admin: get all cadets with their request/attendance status for a date."""

    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()

    cadets = User.query.filter_by(is_admin=False).order_by(User.username).all()
    requests_today = {r.cadet_id: r for r in AttendanceRequest.query.filter_by(date=target_date).all()}
    attendance_today = {a.cadet_id: a for a in Attendance.query.filter_by(date=target_date).all()}

    result = []
    for cadet in cadets:
        req = requests_today.get(cadet.id)
        att = attendance_today.get(cadet.id)
        result.append({
            'id': cadet.id,
            'username': cadet.username,
            'email': cadet.email,
            'roll_no': cadet.roll_no or '—',
            'branch': cadet.branch or '—',
            'has_request': req is not None,
            'requested_at': req.requested_at.strftime('%I:%M %p') if req else None,
            'request_note': req.note if req else None,
            'is_finalized': att is not None,
            'status': att.status if att else ('present' if req else 'absent')  # default based on request
        })

    is_finalized = all(r['is_finalized'] for r in result) if result else False
    present_requests = sum(1 for r in result if r['has_request'])
    finalized_present = sum(1 for r in result if r['is_finalized'] and r['status'] == 'present')

    return jsonify({
        'error': False,
        'date': target_date.strftime('%Y-%m-%d'),
        'display_date': target_date.strftime('%d %B %Y'),
        'total_cadets': len(cadets),
        'requests_received': present_requests,
        'is_finalized': is_finalized,
        'finalized_present': finalized_present,
        'cadets': result
    })


@app.route('/api/attendance/finalize', methods=['POST'])
def api_attendance_finalize():
    """Admin: finalize attendance for a date. Saves present/absent for ALL cadets."""

    data = request.get_json(force=True) or {}
    date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
    # attendance_map: {cadet_id: 'present'|'absent'}
    attendance_map = data.get('attendance', {})

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': True, 'message': 'Invalid date format'}), 400

    cadets = User.query.filter_by(is_admin=False).all()
    saved = 0
    for cadet in cadets:
        status = attendance_map.get(str(cadet.id), 'absent')
        existing = Attendance.query.filter_by(cadet_id=cadet.id, date=target_date).first()
        if existing:
            existing.status = status
            existing.marked_by_admin = True
            existing.marked_at = datetime.utcnow()
        else:
            record = Attendance(
                cadet_id=cadet.id,
                date=target_date,
                status=status,
                marked_by_admin=True
            )
            db.session.add(record)
        saved += 1

    db.session.commit()
    present_count = sum(1 for v in attendance_map.values() if v == 'present')
    absent_count = saved - present_count

    return jsonify({
        'error': False,
        'message': f'Attendance finalized for {target_date.strftime("%d %b %Y")}',
        'saved': saved,
        'present': present_count,
        'absent': absent_count
    })


@app.route('/api/attendance/monthly-report', methods=['GET'])
def api_attendance_monthly():
    """Admin: get monthly report of attendance."""

    today = date.today()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))

    # Get all days in that month that have finalized attendance
    _, days_in_month = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    # Find distinct dates that have been finalized
    finalized_dates = db.session.query(Attendance.date).filter(
        Attendance.date >= month_start,
        Attendance.date <= month_end,
        Attendance.marked_by_admin == True
    ).distinct().order_by(Attendance.date).all()
    finalized_dates = [d[0] for d in finalized_dates]
    total_sessions = len(finalized_dates)

    cadets = User.query.filter_by(is_admin=False).order_by(User.username).all()
    report = []
    for cadet in cadets:
        records = Attendance.query.filter(
            Attendance.cadet_id == cadet.id,
            Attendance.date >= month_start,
            Attendance.date <= month_end,
            Attendance.marked_by_admin == True
        ).all()
        present = sum(1 for r in records if r.status == 'present')
        absent = sum(1 for r in records if r.status == 'absent')
        pct = round((present / total_sessions * 100) if total_sessions > 0 else 0)
        report.append({
            'id': cadet.id,
            'username': cadet.username,
            'email': cadet.email,
            'roll_no': cadet.roll_no or '—',
            'branch': cadet.branch or '—',
            'present': present,
            'absent': absent,
            'total_sessions': total_sessions,
            'percentage': pct
        })

    # Sort by percentage descending
    report.sort(key=lambda x: -x['percentage'])

    import calendar
    return jsonify({
        'error': False,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'total_sessions': total_sessions,
        'finalized_dates': [d.strftime('%d %b') for d in finalized_dates],
        'total_cadets': len(cadets),
        'report': report
    })


# =============================================================================
# NOTICES / EVENTS / GALLERY API
# =============================================================================

@app.route('/api/notices/', methods=['GET', 'POST'])
def api_notices():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        if not title or not category or not description:
            return jsonify({'error': True, 'message': 'Missing required fields'}), 400
        notice = Notice(title=title, category=category, description=description)
        db.session.add(notice)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'notice': notice.to_dict()}), 201

    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return jsonify({'error': False, 'success': True, 'notices': [n.to_dict() for n in notices]})

@app.route('/api/notices/<int:id>', methods=['DELETE'])
def delete_notice(id):
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return jsonify({'error': False, 'success': True})

@app.route('/api/events/', methods=['GET', 'POST'])
def api_events():
    if request.method == 'POST':
        title = request.form.get('title')
        start_date_str = request.form.get('start_date')
        location = request.form.get('location')
        event_type = request.form.get('event_type')
        participants = request.form.get('participants', 0)
        is_mandatory = request.form.get('is_mandatory') == 'true'

        if not title or not start_date_str or not event_type:
            return jsonify({'error': True, 'message': 'Missing required fields'}), 400

        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')) if 'T' in start_date_str else datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            start_date = datetime.utcnow()

        event = Event(title=title, start_date=start_date, location=location,
                      event_type=event_type, participants=participants, is_mandatory=is_mandatory)
        db.session.add(event)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'event': event.to_dict()}), 201

    events = Event.query.order_by(Event.start_date.desc()).all()
    return jsonify({'error': False, 'success': True, 'events': [e.to_dict() for e in events]})

@app.route('/api/events/<int:id>', methods=['DELETE'])
def delete_event(id):
    event = Event.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'error': False, 'success': True})

@app.route('/api/gallery/', methods=['GET', 'POST'])
def api_gallery():
    if request.method == 'POST':
        title = request.form.get('title', 'Photo')
        category = request.form.get('category', 'General')
        file = request.files.get('image')

        if not file or file.filename == '':
            return jsonify({'error': True, 'message': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        gallery_item = GalleryItem(title=title, category=category, image_path=filepath)
        db.session.add(gallery_item)
        db.session.commit()

        return jsonify({'error': False, 'success': True, 'item': gallery_item.to_dict()}), 201

    items = GalleryItem.query.order_by(GalleryItem.uploaded_at.desc()).all()
    return jsonify({'error': False, 'success': True,
                    'items': [i.to_dict() for i in items],
                    'gallery': [i.to_dict() for i in items]})

@app.route('/api/gallery/<int:id>', methods=['DELETE'])
def delete_gallery(id):
    item = GalleryItem.query.get_or_404(id)
    if os.path.exists(item.image_path):
        os.remove(item.image_path)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'error': False, 'success': True})


# =============================================================================
# ADMIN CADET APPROVAL API
# =============================================================================

@app.route('/api/students/enroll', methods=['POST'])
def api_students_enroll():
    """Public: submit enrollment application — creates a pending cadet account."""
    first_name  = request.form.get('first_name', '').strip()
    last_name   = request.form.get('last_name', '').strip()
    email       = request.form.get('email', '').strip().lower()
    roll_no     = request.form.get('roll_number') or request.form.get('roll_no', '')
    branch      = request.form.get('branch', '')
    year        = request.form.get('year', '')
    phone       = request.form.get('phone', '')
    gender      = request.form.get('gender', '')
    blood_group = request.form.get('blood_group', '')
    wing        = request.form.get('wing') or request.form.get('ncc_wing', '')
    motivation  = request.form.get('motivation', '')

    if not email or not first_name:
        return jsonify({'error': True, 'message': 'Name and email are required'}), 400

    # Check if email already registered
    if User.query.filter_by(email=email).first():
        return jsonify({
            'error': False,
            'success': True,
            'already_exists': True,
            'message': 'You have already submitted an application. Please wait for admin approval.',
            'reference_number': 'NCC-' + email.split('@')[0].upper()[:6]
        })

    # Auto-generate a username from name + roll
    username = (first_name[:3] + last_name[:3] + (roll_no[-4:] if roll_no else '')).lower().replace(' ', '')
    if not username or User.query.filter_by(username=username).first():
        import random
        username = f"cadet{random.randint(1000,9999)}"

    # Create account with a temp password (cadet must reset via admin)
    temp_password = generate_password_hash(f"NCC{roll_no or '0000'}@2025", method='pbkdf2:sha256')
    new_cadet = User(
        username=username,
        email=email,
        password_hash=temp_password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
        roll_no=roll_no,
        branch=branch,
        year=year,
        is_admin=False,
        is_approved=False
    )
    db.session.add(new_cadet)
    db.session.commit()

    ref = f"NCC-{str(new_cadet.id).zfill(5)}"
    return jsonify({
        'error': False,
        'success': True,
        'message': 'Enrollment application submitted! The ANO will review and approve your account within 3–5 days.',
        'reference_number': ref,
        'username': username
    }), 201

@app.route('/api/students/', methods=['GET'])
def api_admin_all_cadets():
    """Admin: get all cadets."""
    cadets = User.query.filter_by(is_admin=False).all()
    return jsonify({
        'error': False,
        'students': [{
            'id': c.id,
            'username': c.username,
            'email': c.email,
            'first_name': c.first_name or '',
            'last_name': c.last_name or '',
            'phone_number': c.phone_number or '',
            'roll_no': c.roll_no or '—',
            'branch': c.branch or '—',
            'year': c.year or '—',
            'status': 'approved' if c.is_approved else 'pending'
        } for c in cadets]
    })

@app.route('/api/admin/pending-cadets', methods=['GET'])
def api_admin_pending_cadets():
    """Admin: get all cadets pending approval."""
    pending = User.query.filter_by(is_admin=False, is_approved=False).all()
    return jsonify({
        'error': False,
        'cadets': [{
            'id': c.id,
            'username': c.username,
            'email': c.email,
            'first_name': c.first_name or '',
            'last_name': c.last_name or '',
            'phone_number': c.phone_number or '',
            'roll_no': c.roll_no or '—',
            'branch': c.branch or '—',
            'year': c.year or '—'
        } for c in pending]
    })

@app.route('/api/admin/approve-cadet', methods=['POST'])
def api_admin_approve_cadet():
    """Admin: approve or reject a pending cadet."""
    data = request.get_json(force=True) or {}
    cadet_id = data.get('cadet_id')
    action = data.get('action') # 'approve' or 'reject'

    cadet = User.query.get(cadet_id)
    if not cadet or cadet.is_admin:
        return jsonify({'error': True, 'message': 'Cadet not found'}), 404

    if action == 'approve':
        cadet.is_approved = True
        db.session.commit()
        return jsonify({'error': False, 'message': 'Cadet approved successfully'})
    elif action == 'reject':
        db.session.delete(cadet)
        db.session.commit()
        return jsonify({'error': False, 'message': 'Cadet rejected and removed'})
    else:
        return jsonify({'error': True, 'message': 'Invalid action'}), 400

@app.route('/api/students/<int:id>', methods=['DELETE'])
def api_delete_student(id):
    """Admin: permanently delete a cadet account."""
    cadet = User.query.get(id)
    if not cadet or cadet.is_admin:
        return jsonify({'error': True, 'message': 'Cadet not found'}), 404
    # Also clean up their attendance records
    Attendance.query.filter_by(cadet_id=id).delete()
    AttendanceRequest.query.filter_by(cadet_id=id).delete()
    db.session.delete(cadet)
    db.session.commit()
    return jsonify({'error': False, 'success': True, 'message': 'Cadet deleted successfully'})


# =============================================================================
# CONTACT FORM API
# =============================================================================

@app.route('/api/contact/', methods=['GET', 'POST'])
def api_contact():
    if request.method == 'POST':
        data = request.get_json(force=True) or {}
        # also support form data
        name    = data.get('name') or request.form.get('name', '')
        email   = data.get('email') or request.form.get('email', '')
        subject = data.get('subject') or request.form.get('subject', '')
        message = data.get('message') or request.form.get('message', '')
        if not name or not email or not message:
            return jsonify({'error': True, 'message': 'Name, email and message are required'}), 400
        contact = Contact(name=name, email=email, subject=subject, message=message)
        db.session.add(contact)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'Message received! We will get back to you soon.'}), 201

    # GET — admin views all messages
    contacts = Contact.query.order_by(Contact.created_at.desc()).all()
    return jsonify({'error': False, 'success': True, 'contacts': [c.to_dict() for c in contacts]})

@app.route('/api/contact/<int:id>/read', methods=['PATCH'])
def api_contact_read(id):
    contact = Contact.query.get_or_404(id)
    contact.is_read = True
    db.session.commit()
    return jsonify({'error': False, 'success': True})

@app.route('/api/contact/<int:id>', methods=['DELETE'])
def api_contact_delete(id):
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()
    return jsonify({'error': False, 'success': True})


# =============================================================================
# ACHIEVEMENTS API
# =============================================================================

@app.route('/api/achievements/', methods=['GET', 'POST'])
def api_achievements():
    if request.method == 'POST':
        cadet = request.form.get('cadet') or request.form.get('ach-cadet', '')
        award = request.form.get('award') or request.form.get('ach-award', '')
        ach_type = request.form.get('type') or request.form.get('ach-type', '')
        ach_date = request.form.get('date') or request.form.get('ach-date', '')
        if not cadet or not award:
            return jsonify({'error': True, 'message': 'Cadet name and award are required'}), 400
        achievement = Achievement(
            cadet=cadet, award=award,
            achievement_type=ach_type,
            date=ach_date or datetime.utcnow().strftime('%Y-%m-%d')
        )
        db.session.add(achievement)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'achievement': achievement.to_dict()}), 201

    achievements = Achievement.query.order_by(Achievement.created_at.desc()).all()
    return jsonify({'error': False, 'success': True, 'achievements': [a.to_dict() for a in achievements]})

@app.route('/api/achievements/<int:id>', methods=['DELETE'])
def api_delete_achievement(id):
    achievement = Achievement.query.get_or_404(id)
    db.session.delete(achievement)
    db.session.commit()
    return jsonify({'error': False, 'success': True})


# =============================================================================
# DASHBOARD STATS API (real data)
# =============================================================================

@app.route('/api/dashboard/stats', methods=['GET'])
def api_dashboard_stats():
    """Returns real-time stats for the admin dashboard."""
    total_cadets      = User.query.filter_by(is_admin=False).count()
    approved_cadets   = User.query.filter_by(is_admin=False, is_approved=True).count()
    pending_cadets    = User.query.filter_by(is_admin=False, is_approved=False).count()
    total_events      = Event.query.count()
    active_notices    = Notice.query.count()
    total_achievements = Achievement.query.count()
    total_contacts    = Contact.query.filter_by(is_read=False).count()

    today = date.today()
    present_today = Attendance.query.filter_by(date=today, status='present').count()
    attendance_pct = round((present_today / total_cadets * 100) if total_cadets > 0 else 0)

    # Monthly enrollment trend (last 6 months)
    trend = []
    for i in range(5, -1, -1):
        import calendar
        m = (today.month - i - 1) % 12 + 1
        y = today.year - ((today.month - i - 1) // 12)
        count = User.query.filter(
            db.extract('month', User.created_at) == m,
            db.extract('year',  User.created_at) == y,
            User.is_admin == False
        ).count()
        trend.append({'month': calendar.month_abbr[m], 'year': y, 'count': count})

    return jsonify({
        'error': False,
        'success': True,
        'total_cadets': total_cadets,
        'approved_cadets': approved_cadets,
        'pending_cadets': pending_cadets,
        'total_events': total_events,
        'active_notices': active_notices,
        'total_achievements': total_achievements,
        'unread_contacts': total_contacts,
        'present_today': present_today,
        'attendance_pct': attendance_pct,
        'enrollment_trend': trend
    })


# =============================================================================
# PUBLIC STATS API
# =============================================================================

@app.route('/api/stats/public', methods=['GET'])
def api_public_stats():
    """Public stats shown on the home page."""
    total_cadets      = User.query.filter_by(is_admin=False, is_approved=True).count()
    total_events      = Event.query.count()
    total_notices     = Notice.query.count()
    total_achievements = Achievement.query.count()
    return jsonify({
        'error': False,
        'total_cadets': total_cadets,
        'total_events': total_events,
        'total_notices': total_notices,
        'total_achievements': total_achievements
    })


# =============================================================================
# ATTENDANCE ALIAS ROUTES (used by admin dashboard legacy JS)
# =============================================================================

@app.route('/api/attendance/admin-summary', methods=['GET'])
def api_attendance_admin_summary():
    """Alias for /api/attendance/daily — used by old admin dashboard JS."""
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()

    cadets = User.query.filter_by(is_admin=False, is_approved=True).order_by(User.username).all()
    attendance_today = {a.cadet_id: a for a in Attendance.query.filter_by(date=target_date).all()}

    result = []
    for cadet in cadets:
        att = attendance_today.get(cadet.id)
        result.append({
            'id': cadet.id,
            'username': cadet.username,
            'email': cadet.email,
            'roll_no': cadet.roll_no or '—',
            'marked_today': att is not None and att.status == 'present',
            'status': att.status if att else 'absent'
        })

    return jsonify({'error': False, 'date': date_str, 'cadets': result})


@app.route('/api/attendance/admin-mark', methods=['POST'])
def api_attendance_admin_mark():
    """Mark a single cadet present/absent — used by admin dashboard toggle buttons."""
    data = request.get_json(force=True) or {}
    cadet_id = data.get('cadet_id')
    status   = data.get('status', 'present')
    date_str = data.get('date', date.today().strftime('%Y-%m-%d'))

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': True, 'message': 'Invalid date'}), 400

    cadet = User.query.get(cadet_id)
    if not cadet or cadet.is_admin:
        return jsonify({'error': True, 'message': 'Cadet not found'}), 404

    existing = Attendance.query.filter_by(cadet_id=cadet_id, date=target_date).first()
    if existing:
        existing.status = status
        existing.marked_by_admin = True
        existing.marked_at = datetime.utcnow()
    else:
        record = Attendance(cadet_id=cadet_id, date=target_date,
                            status=status, marked_by_admin=True)
        db.session.add(record)
    db.session.commit()
    return jsonify({'error': False, 'success': True,
                    'message': f'{cadet.username} marked {status}'})


@app.route('/api/attendance/admin-mark-all', methods=['POST'])
def api_attendance_admin_mark_all():
    """Mark ALL approved cadets as present for a date — used by Mark All Present button."""
    data = request.get_json(force=True) or {}
    date_str = data.get('date', date.today().strftime('%Y-%m-%d'))

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': True, 'message': 'Invalid date'}), 400

    cadets = User.query.filter_by(is_admin=False, is_approved=True).all()
    count = 0
    for cadet in cadets:
        existing = Attendance.query.filter_by(cadet_id=cadet.id, date=target_date).first()
        if existing:
            existing.status = 'present'
            existing.marked_by_admin = True
            existing.marked_at = datetime.utcnow()
        else:
            db.session.add(Attendance(cadet_id=cadet.id, date=target_date,
                                      status='present', marked_by_admin=True))
        count += 1
    db.session.commit()
    return jsonify({'error': False, 'success': True,
                    'message': f'All {count} cadets marked present for {date_str}'})


@app.route('/api/attendance/my', methods=['GET'])
def api_attendance_my():
    """Alias for /api/attendance/my-status — used by admin cadet history modal."""
    return api_my_attendance_status()


# Run the app
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
