from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import date, datetime, timedelta, timezone
from calendar import monthrange

def utcnow_helper():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from models import db, User, Notice, GalleryItem, Attendance, AttendanceRequest, Event, Contact, Achievement, Camp, CampApplication, PushSubscription, SmsAlert, LeaveRequest
import json

# VAPID & Twilio Configurations for PWA Push & SMS Alerts
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL', 'mailto:ano@ncc.portal')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Try importing pywebpush dynamically
try:
    from pywebpush import webpush, WebPushException
    PYWEBPUSH_AVAILABLE = True
except ImportError:
    PYWEBPUSH_AVAILABLE = False
    print("Warning: pywebpush library not installed. PWA notifications will run in simulation mode.")

# Try importing twilio dynamically
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Warning: twilio library not installed. SMS alerts will run in simulation mode.")

def send_cadet_alert(user_id, message, title='NCC Update', channels=None, scheduled_at=None, category='info', existing_alert_id=None):
    """Centralized dispatcher to send PWA push notifications and SMS alerts to a cadet."""
    if channels is None:
        channels = ['push', 'sms']
        
    user = User.query.get(user_id)
    if not user:
        return False

    # Handle scheduling for later delivery
    if scheduled_at:
        try:
            phone_normalized = user.phone_number or 'PWA Push'
            if phone_normalized and phone_normalized.strip() and not phone_normalized.strip().startswith('+') and phone_normalized.strip() != 'PWA Push':
                p_norm = phone_normalized.strip()
                if len(p_norm) == 10 and p_norm.isdigit():
                    phone_normalized = '+91' + p_norm
                elif p_norm.isdigit():
                    phone_normalized = '+' + p_norm

            alert_log = SmsAlert(
                user_id=user.id,
                receiver_phone=phone_normalized,
                message_title=title,
                message_body=message,
                status='scheduled',
                scheduled_at=scheduled_at,
                category=category
            )
            db.session.add(alert_log)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Failed to save scheduled alert: {e}")
            return False

    # 1. Dispatch SMS/WhatsApp + Always log to DB for cadet in-app inbox
    if 'sms' in channels:
        phone = user.phone_number
        sms_status = 'simulated'
        error_msg = None
        phone_normalized = 'In-App'  # Default: no phone = in-app only

        if phone and phone.strip():
            # Normalize phone number
            phone_normalized = phone.strip()
            if not phone_normalized.startswith('+'):
                if len(phone_normalized) == 10 and phone_normalized.isdigit():
                    phone_normalized = '+91' + phone_normalized
                elif phone_normalized.isdigit():
                    phone_normalized = '+' + phone_normalized

            if TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
                try:
                    client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    client.messages.create(
                        body=f"[{title}] {message}",
                        from_=TWILIO_PHONE_NUMBER,
                        to=phone_normalized
                    )
                    sms_status = 'sent'
                except Exception as e:
                    sms_status = 'failed'
                    error_msg = str(e)
                    print(f"Twilio SMS delivery failed: {e}")
            else:
                # Simulated SMS Logging
                sms_status = 'simulated'
                try:
                    os.makedirs('instance', exist_ok=True)
                    log_path = os.path.join('instance', 'sms_logs.txt')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{utcnow_helper().isoformat()}] TO: {phone_normalized} | MSG: [{title}] {message}\n")
                except Exception as log_err:
                    print(f"Failed to write to sms_logs.txt: {log_err}")
        else:
            # No phone number — mark as in-app only, still log for portal inbox
            sms_status = 'simulated'
            error_msg = 'No phone registered — in-app only'

        # ALWAYS save to database SmsAlert for cadet inbox (regardless of phone)
        try:
            alert_log = None
            if existing_alert_id:
                alert_log = SmsAlert.query.get(existing_alert_id)

            if alert_log:
                alert_log.receiver_phone = phone_normalized
                alert_log.message_title = title
                alert_log.message_body = message
                alert_log.status = sms_status
                alert_log.sent_at = utcnow_helper()
                alert_log.error_message = error_msg
                alert_log.category = category
            else:
                alert_log = SmsAlert(
                    user_id=user.id,
                    receiver_phone=phone_normalized,
                    message_title=title,
                    message_body=message,
                    status=sms_status,
                    error_message=error_msg,
                    category=category
                )
                db.session.add(alert_log)
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            print(f"Failed to log SMS/In-App alert in DB: {db_err}")

    # 2. Dispatch PWA Web Push
    if 'push' in channels:
        subscriptions = PushSubscription.query.filter_by(user_id=user.id).all()
        pwa_status = 'simulated'
        pwa_err = None
        for sub in subscriptions:
            payload = json.dumps({
                'title': title,
                'body': message,
                'icon': '/images/logo.png',
                'badge': '/images/logo.png',
                'url': '/pages/cadet-portal.html',
                'category': category
            })
            
            if PYWEBPUSH_AVAILABLE and VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY:
                try:
                    subscription_info = {
                        'endpoint': sub.endpoint,
                        'keys': {
                            'p256dh': sub.p256dh,
                            'auth': sub.auth
                        }
                    }
                    webpush(
                        subscription_info=subscription_info,
                        data=payload,
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": VAPID_CLAIM_EMAIL}
                    )
                    pwa_status = 'sent'
                except WebPushException as ex:
                    print(f"Web Push delivery error for sub {sub.id}: {ex}")
                    pwa_status = 'failed'
                    pwa_err = str(ex)
                    if ex.response and ex.response.status_code in [404, 410]:
                        try:
                            db.session.delete(sub)
                            db.session.commit()
                            print(f"Removed expired/invalid PWA subscription: {sub.endpoint}")
                        except Exception as del_err:
                            db.session.rollback()
                            print(f"Failed to delete expired subscription: {del_err}")
                except Exception as e:
                    print(f"Web Push unknown error: {e}")
                    pwa_status = 'failed'
                    pwa_err = str(e)
            else:
                # Simulated Console Push Notification
                pwa_status = 'simulated'
                print(f"[SIMULATED PUSH] TO User: {user.username} | Title: {title} | Body: {message}")
        
        if 'sms' not in channels:
            try:
                alert_log = None
                if existing_alert_id:
                    alert_log = SmsAlert.query.get(existing_alert_id)
                
                if alert_log:
                    alert_log.receiver_phone = 'PWA Push'
                    alert_log.message_title = title
                    alert_log.message_body = message
                    alert_log.status = pwa_status
                    alert_log.sent_at = utcnow_helper()
                    alert_log.error_message = pwa_err or 'PWA Simulated'
                    alert_log.category = category
                else:
                    alert_log = SmsAlert(
                        user_id=user.id,
                        receiver_phone='PWA Push',
                        message_title=title,
                        message_body=message,
                        status=pwa_status,
                        error_message=pwa_err or 'PWA Simulated',
                        category=category
                    )
                    db.session.add(alert_log)
                db.session.commit()
            except Exception as db_err:
                db.session.rollback()
                print(f"Failed to log Push alert in DB: {db_err}")

    return True

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_override_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ncc_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('images', 'uploads')

# --- Lightweight In-Memory Rate Limiting for Login ---
login_attempts = {}

def is_rate_limited(ip, limit=5, window=60):
    now = datetime.now()
    cutoff = now - timedelta(seconds=window)
    attempts = [t for t in login_attempts.get(ip, []) if t > cutoff]
    login_attempts[ip] = attempts
    if len(attempts) >= limit:
        return True
    return False

def record_attempt(ip):
    if ip not in login_attempts:
        login_attempts[ip] = []
    login_attempts[ip].append(datetime.now())

# --- Content Security Policy & Security Headers Hook ---
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self' https: 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https:; font-src 'self' https: data:; frame-src 'self' https://www.google.com;"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

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
    # Seed default achievements if empty
    try:
        if Achievement.query.count() == 0:
            db.session.add(Achievement(cadet='Arjun Sharma', award='Best Cadet Award (CATC)', date='2025-05-10', achievement_type='Award'))
            db.session.add(Achievement(cadet='Anjali Rani', award='Gold Medal in Shooting (RDC)', date='2025-01-26', achievement_type='Competition'))
            db.session.add(Achievement(cadet='Priya Verma', award='Naval Camp Parade Commander', date='2025-02-14', achievement_type='Camp'))
            db.session.commit()
            print("Migration: Seeded default achievements.")
    except Exception as e:
        db.session.rollback()
        print(f"Migration error seeding achievements: {e}")
    # Robust migration check for cert_a_approved and cert_b_approved columns
    try:
        from sqlalchemy import text
        columns_res = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
        column_names = [col[1] for col in columns_res]
        
        if 'cert_a_approved' not in column_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN cert_a_approved BOOLEAN DEFAULT 0"))
            print("Migration: Added cert_a_approved column to user table.")
        if 'cert_b_approved' not in column_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN cert_b_approved BOOLEAN DEFAULT 0"))
            print("Migration: Added cert_b_approved column to user table.")
        if 'wing' not in column_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN wing VARCHAR(50) DEFAULT 'Army'"))
            print("Migration: Added wing column to user table.")
        if 'reset_token' not in column_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN reset_token VARCHAR(100)"))
            print("Migration: Added reset_token column to user table.")
        if 'reset_token_expiry' not in column_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN reset_token_expiry DATETIME"))
            print("Migration: Added reset_token_expiry column to user table.")
        if 'profile_photo' not in column_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN profile_photo VARCHAR(255)"))
            print("Migration: Added profile_photo column to user table.")
            
        # SMS Alert table migrations for scheduled alerts
        alert_cols = db.session.execute(text("PRAGMA table_info(sms_alert)")).fetchall()
        alert_col_names = [col[1] for col in alert_cols]
        if 'scheduled_at' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN scheduled_at DATETIME"))
            print("Migration: Added scheduled_at column to sms_alert table.")
        if 'category' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN category VARCHAR(50) DEFAULT 'info'"))
            print("Migration: Added category column to sms_alert table.")
        if 'is_read' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN is_read BOOLEAN DEFAULT 0"))
            print("Migration: Added is_read column to sms_alert table.")
        if 'is_direct' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN is_direct BOOLEAN DEFAULT 0"))
            print("Migration: Added is_direct column to sms_alert table.")
        if 'message_title' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN message_title VARCHAR(150) DEFAULT 'NCC Announcement'"))
            print("Migration: Added message_title column to sms_alert table.")

        # ── Tier 1 migrations ──────────────────────────────────────────────
        if 'requires_acknowledgement' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN requires_acknowledgement BOOLEAN DEFAULT 0"))
            print("Migration: Added requires_acknowledgement column.")
        if 'is_acknowledged' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN is_acknowledged BOOLEAN DEFAULT 0"))
            print("Migration: Added is_acknowledged column.")
        if 'acknowledged_at' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN acknowledged_at DATETIME"))
            print("Migration: Added acknowledged_at column.")
        if 'is_emergency' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN is_emergency BOOLEAN DEFAULT 0"))
            print("Migration: Added is_emergency column.")
        if 'target_group' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN target_group VARCHAR(50) DEFAULT 'all'"))
            print("Migration: Added target_group column.")

        # ── Tier 2 migrations ──────────────────────────────────────────────
        if 'email_channel' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN email_channel BOOLEAN DEFAULT 0"))
            print("Migration: Added email_channel column.")
        if 'whatsapp_channel' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN whatsapp_channel BOOLEAN DEFAULT 0"))
            print("Migration: Added whatsapp_channel column.")
        if 'is_recurring' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN is_recurring BOOLEAN DEFAULT 0"))
            print("Migration: Added is_recurring column.")
        if 'recurrence_type' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN recurrence_type VARCHAR(20)"))
            print("Migration: Added recurrence_type column.")
        if 'recurrence_interval' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN recurrence_interval INTEGER DEFAULT 1"))
            print("Migration: Added recurrence_interval column.")
        if 'next_recurrence_at' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN next_recurrence_at DATETIME"))
            print("Migration: Added next_recurrence_at column.")
        if 'reminder_hours' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN reminder_hours INTEGER"))
            print("Migration: Added reminder_hours column.")
        if 'reminder_sent' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN reminder_sent BOOLEAN DEFAULT 0"))
            print("Migration: Added reminder_sent column.")
        if 'expires_at' not in alert_col_names:
            db.session.execute(text("ALTER TABLE sms_alert ADD COLUMN expires_at DATETIME"))
            print("Migration: Added expires_at column.")

        db.session.commit()

        # ── leave_request table migrations ────────────────────────────────
        try:
            leave_cols = db.session.execute(text("PRAGMA table_info(leave_request)")).fetchall()
            leave_col_names = [col[1] for col in leave_cols]
            if 'leave_type' not in leave_col_names:
                db.session.execute(text("ALTER TABLE leave_request ADD COLUMN leave_type VARCHAR(50) DEFAULT 'Personal'"))
                print("Migration: Added leave_type column to leave_request table.")
            if 'updated_at' not in leave_col_names:
                db.session.execute(text("ALTER TABLE leave_request ADD COLUMN updated_at DATETIME"))
                print("Migration: Added updated_at column to leave_request table.")
            db.session.commit()
        except Exception as e:
            print(f"Leave request migration error: {e}")

    except Exception as e:
        print("Migration check or columns add failed:", e)


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
    from flask import make_response
    response = make_response(send_from_directory('.', 'sw.js'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

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
        return jsonify({'message': 'Admin already exists. Login with admin@ncc-gph.ac.in and ncc@admin123'})
    admin = User(
        username='admin',
        email='admin@ncc-gph.ac.in',
        password_hash=generate_password_hash('ncc@admin123', method='pbkdf2:sha256'),
        is_admin=True,
        is_approved=True
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({'message': 'Admin created successfully! Email: admin@ncc-gph.ac.in | Password: ncc@admin123'})

# --- Catch-all for /pages/<name>.html links (from static site) ---
@app.route('/pages/<path:filename>')
def serve_page(filename):
    template_name = filename if filename.endswith('.html') else filename + '.html'
    if 'certificate' in template_name.lower():
        if current_user.is_authenticated and not current_user.is_admin:
            if current_user.cert_a_approved:
                return redirect(url_for('api_certificates_download', cert_type='A'))
            elif current_user.cert_b_approved:
                return redirect(url_for('api_certificates_download', cert_type='B'))
            else:
                flash("You do not have any approved certificates to view.")
                return redirect('/pages/cadet-portal.html')
        else:
            flash("Please login as a cadet to view your certificate.")
            return redirect('/login')
    return render_template(template_name)

@app.after_request
def add_no_cache_headers(response):
    """Prevent HTML pages from being cached so changes always show immediately."""
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


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
        year=year,
        wing=data.get('wing', 'Army')
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'error': False, 'message': 'Registered successfully'})

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    if is_rate_limited(client_ip):
        return jsonify({'error': True, 'message': 'Too many login attempts. Please try again after 60 seconds.'}), 429
    
    record_attempt(client_ip)

    data = request.get_json(force=True) or {}
    username_or_email = data.get('username', '').strip() or data.get('email', '').strip()
    password = data.get('password', '')

    from sqlalchemy import func
    user = User.query.filter(
        (func.lower(User.email) == username_or_email.lower()) | 
        (func.lower(User.username) == username_or_email.lower())
    ).first()
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

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_auth_forgot_password():
    data = request.get_json(force=True) or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': True, 'message': 'Email address is required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({
            'error': False,
            'message': 'If this email is registered, a password reset token has been simulated.'
        })
    
    import random
    token = str(random.randint(100000, 999999))
    user.reset_token = token
    user.reset_token_expiry = utcnow_helper() + timedelta(minutes=15)
    db.session.commit()
    
    try:
        os.makedirs('instance', exist_ok=True)
        with open(os.path.join('instance', 'email_logs.txt'), 'a', encoding='utf-8') as f:
            f.write(f"[{utcnow_helper().isoformat()}] PASSWORD RESET simulated TO: {email} | TOKEN: {token}\n")
    except Exception:
        pass

    return jsonify({
        'error': False,
        'message': f'A password reset token has been generated. For testing/demo, your token is: {token}',
        'token': token
    })

@app.route('/api/auth/reset-password', methods=['POST'])
def api_auth_reset_password():
    data = request.get_json(force=True) or {}
    email = data.get('email', '').strip()
    token = data.get('token', '').strip()
    new_password = data.get('password', '')
    
    if not email or not token or not new_password:
        return jsonify({'error': True, 'message': 'Email, token, and new password are required'}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user or user.reset_token != token:
        return jsonify({'error': True, 'message': 'Invalid token or email address'}), 400
        
    if user.reset_token_expiry < utcnow_helper():
        return jsonify({'error': True, 'message': 'Reset token has expired. Please request a new one.'}), 400
        
    user.password_hash = generate_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    
    return jsonify({'error': False, 'message': 'Password has been reset successfully! You can now login.'})

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
            'theme_preference': current_user.theme_preference or 'system',
            'wing': current_user.wing or 'Army',
            'profile_photo': current_user.profile_photo or '',
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
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
    if 'wing' in data: current_user.wing = data['wing'].strip()
    if 'theme_preference' in data: current_user.theme_preference = data['theme_preference'].strip()

    # Note: Roll Number, Email, and Username are typically read-only or handled via separate secure processes.
    db.session.commit()
    return jsonify({'error': False, 'message': 'Settings updated successfully'})

@app.route('/api/cadet/upload-photo', methods=['POST'])
@login_required
def api_cadet_upload_photo():
    if current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin cannot upload cadet photos'}), 400
        
    if 'photo' not in request.files:
        return jsonify({'error': True, 'message': 'No file part in the request'}), 400
        
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': True, 'message': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filename = f"avatar_{current_user.username}_{utcnow_helper().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        photo_url = f"/images/uploads/{filename}"
        current_user.profile_photo = photo_url
        db.session.commit()
        
        return jsonify({
            'error': False,
            'message': 'Profile photo uploaded successfully!',
            'photo_url': photo_url
        })
    
    return jsonify({'error': True, 'message': 'Failed to save photo'}), 400

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
            { 'type': 'A Certificate', 'available': current_user.cert_a_approved, 'download_url': '/api/certificates/download/A' if current_user.cert_a_approved else None },
            { 'type': 'B Certificate', 'available': current_user.cert_b_approved, 'download_url': '/api/certificates/download/B' if current_user.cert_b_approved else None },
        ]
    })

@app.route('/api/certificates/download/<string:cert_type>', methods=['GET'])
@login_required
def api_certificates_download(cert_type):
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    if cert_type == 'A' and not current_user.cert_a_approved:
        flash("You do not have approval for Certificate A.")
        return redirect('/pages/cadet-portal.html')
    if cert_type == 'B' and not current_user.cert_b_approved:
        flash("You do not have approval for Certificate B.")
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
@login_required
def api_attendance_daily():
    """Admin: get all cadets with their request/attendance status for a date."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()

    cadets = User.query.filter_by(is_admin=False).order_by(User.username).all()
    requests_today = {r.cadet_id: r for r in AttendanceRequest.query.filter_by(date=target_date).all()}
    attendance_today = {a.cadet_id: a for a in Attendance.query.filter_by(date=target_date).all()}

    # Query approved leaves covering target_date
    leaves_today = LeaveRequest.query.filter(
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date <= target_date,
        LeaveRequest.end_date >= target_date
    ).all()
    leaves_map = {l.cadet_id: l for l in leaves_today}

    result = []
    for cadet in cadets:
        req = requests_today.get(cadet.id)
        att = attendance_today.get(cadet.id)
        leave = leaves_map.get(cadet.id)
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
            'on_leave': leave is not None,
            'leave_reason': leave.reason if leave else None,
            'status': att.status if att else ('leave' if leave else ('present' if req else 'absent'))  # default to leave if on approved leave
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
@login_required
def api_attendance_finalize():
    """Admin: finalize attendance for a date. Saves present/absent for ALL cadets."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

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
            existing.marked_at = utcnow_helper()
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
    leave_count = sum(1 for v in attendance_map.values() if v == 'leave')
    absent_count = saved - present_count - leave_count

    return jsonify({
        'error': False,
        'message': f'Attendance finalized for {target_date.strftime("%d %b %Y")}',
        'saved': saved,
        'present': present_count,
        'absent': absent_count,
        'leave': leave_count
    })


@app.route('/api/attendance/monthly-report', methods=['GET'])
@login_required
def api_attendance_monthly():
    """Admin: get monthly report of attendance."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

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
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        if not title or not category or not description:
            return jsonify({'error': True, 'message': 'Missing required fields'}), 400
        notice = Notice(title=title, category=category, description=description)
        db.session.add(notice)
        db.session.commit()
        
        # Dispatch notifications to all approved cadets
        try:
            cadets = User.query.filter_by(is_admin=False, is_approved=True).all()
            for cadet in cadets:
                send_cadet_alert(cadet.id, f"New Notice: {title}", title=category)
        except Exception as e:
            print(f"Error broadcasting notice alert: {e}")

        return jsonify({'error': False, 'success': True, 'notice': notice.to_dict()}), 201

    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return jsonify({'error': False, 'success': True, 'notices': [n.to_dict() for n in notices]})

@app.route('/api/notices/<int:id>', methods=['DELETE'])
@login_required
def delete_notice(id):
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return jsonify({'error': False, 'success': True})

@app.route('/api/events/', methods=['GET', 'POST'])
def api_events():
    if request.method == 'POST':
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
            start_date = utcnow_helper()

        event = Event(title=title, start_date=start_date, location=location,
                      event_type=event_type, participants=participants, is_mandatory=is_mandatory)
        db.session.add(event)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'event': event.to_dict()}), 201

    events = Event.query.order_by(Event.start_date.desc()).all()
    return jsonify({'error': False, 'success': True, 'events': [e.to_dict() for e in events]})

@app.route('/api/events/<int:id>', methods=['DELETE'])
@login_required
def delete_event(id):
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    event = Event.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'error': False, 'success': True})

@app.route('/api/gallery/', methods=['GET', 'POST'])
def api_gallery():
    if request.method == 'POST':
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
        title = request.form.get('title', 'Photo')
        category = request.form.get('category', 'General')
        file = request.files.get('image')

        if not file or file.filename == '':
            return jsonify({'error': True, 'message': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        filename = f"{utcnow_helper().strftime('%Y%m%d%H%M%S')}_{filename}"
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
@login_required
def delete_gallery(id):
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    item = GalleryItem.query.get_or_404(id)
    if os.path.exists(item.image_path):
        os.remove(item.image_path)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'error': False, 'success': True})


# =============================================================================
# CAMP APPLICATION & SELECTION MATRIX API
# =============================================================================

@app.route('/api/camps/', methods=['GET', 'POST'])
def api_camps():
    """Get all camps (GET) or create a new camp (POST, Admin only)."""
    if request.method == 'POST':
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
        
        data = request.get_json(silent=True) or {}
        title = data.get('title') or request.form.get('title')
        location = data.get('location') or request.form.get('location')
        start_date_str = data.get('start_date') or request.form.get('start_date')
        end_date_str = data.get('end_date') or request.form.get('end_date')
        camp_type = data.get('camp_type') or request.form.get('camp_type', 'Annual')
        vacancies = int(data.get('vacancies') or request.form.get('vacancies', 50))
        eligibility = data.get('eligibility') or request.form.get('eligibility', 'All')
        description = data.get('description') or request.form.get('description')

        if not title or not start_date_str or not end_date_str:
            return jsonify({'error': True, 'message': 'Missing required fields'}), 400

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': True, 'message': 'Invalid date format (use YYYY-MM-DD)'}), 400

        camp = Camp(
            title=title, location=location, start_date=start_date, end_date=end_date,
            camp_type=camp_type, vacancies=vacancies, eligibility=eligibility,
            status='open', description=description
        )
        db.session.add(camp)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'camp': camp.to_dict()}), 201

    camps = Camp.query.order_by(Camp.start_date.desc()).all()
    return jsonify({'error': False, 'success': True, 'camps': [c.to_dict() for c in camps]})

@app.route('/api/camps/<int:id>', methods=['DELETE'])
@login_required
def delete_camp(id):
    """Admin: permanently delete a camp."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    camp = Camp.query.get_or_404(id)
    db.session.delete(camp)
    db.session.commit()
    return jsonify({'error': False, 'success': True, 'message': 'Camp deleted successfully'})

@app.route('/api/camps/<int:id>/status', methods=['POST'])
@login_required
def update_camp_status(id):
    """Admin: change camp status (open or closed)."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    camp = Camp.query.get_or_404(id)
    data = request.get_json(force=True) or {}
    status = data.get('status')
    if status not in ['open', 'closed']:
        return jsonify({'error': True, 'message': 'Invalid status. Must be open or closed'}), 400
    camp.status = status
    db.session.commit()

    # Broadcast alert to all cadets
    try:
        msg = f"The camp '{camp.title}' is now {status} for applications."
        if status == 'open':
            msg += " Visit the Cadet Portal to apply now!"
        cadets = User.query.filter_by(is_admin=False, is_approved=True).all()
        for cadet in cadets:
            send_cadet_alert(cadet.id, msg, title=f"Camp Registration {status.capitalize()}")
    except Exception as e:
        print(f"Error broadcasting camp status change: {e}")

    return jsonify({'error': False, 'success': True, 'message': f'Camp status updated to {status}', 'camp': camp.to_dict()})

@app.route('/api/camps/apply', methods=['POST'])
@login_required
def apply_for_camp():
    """Cadet: submit an application for an open camp."""
    if current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admins cannot apply for camps'}), 400

    data = request.get_json(force=True) or {}
    camp_id = data.get('camp_id')
    height = data.get('height')
    weight = data.get('weight')
    medical_status = data.get('medical_status', 'Fit')
    past_camps = data.get('past_camps', '')

    if not camp_id:
        return jsonify({'error': True, 'message': 'Camp ID is required'}), 400

    camp = Camp.query.get(camp_id)
    if not camp:
        return jsonify({'error': True, 'message': 'Camp not found'}), 404
    if camp.status != 'open':
        return jsonify({'error': True, 'message': 'This camp is closed for applications'}), 400

    existing = CampApplication.query.filter_by(camp_id=camp_id, cadet_id=current_user.id).first()
    if existing:
        return jsonify({'error': True, 'message': 'You have already applied for this camp'}), 400

    try:
        height = float(height) if height else None
        weight = float(weight) if weight else None
    except ValueError:
        return jsonify({'error': True, 'message': 'Height and weight must be numeric values'}), 400

    appln = CampApplication(
        camp_id=camp_id, cadet_id=current_user.id,
        height=height, weight=weight, medical_status=medical_status,
        past_camps=past_camps, status='pending'
    )
    db.session.add(appln)
    db.session.commit()
    return jsonify({'error': False, 'success': True, 'application': appln.to_dict()}), 201

@app.route('/api/camps/applications/mine', methods=['GET'])
@login_required
def get_my_camp_applications():
    """Cadet: get all camp applications submitted by current user."""
    applns = CampApplication.query.filter_by(cadet_id=current_user.id).all()
    return jsonify({'error': False, 'success': True, 'applications': [a.to_dict() for a in applns]})

@app.route('/api/admin/camp-applications', methods=['GET'])
@login_required
def get_all_camp_applications():
    """Admin: get all camp applications with calculated cadet attendance %."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    applns = CampApplication.query.all()
    
    cadet_ids = list(set(a.cadet_id for a in applns))
    attendance_map = {}
    
    total_finalized = db.session.query(db.func.count(db.distinct(Attendance.date))).filter(Attendance.marked_by_admin == True).scalar() or 0
    
    for c_id in cadet_ids:
        if total_finalized > 0:
            present_days = Attendance.query.filter_by(cadet_id=c_id, status='present').count()
            pct = round((present_days / total_finalized) * 100)
        else:
            pct = 100
        attendance_map[c_id] = pct

    result = []
    for a in applns:
        d = a.to_dict()
        d['cadet_attendance_pct'] = attendance_map.get(a.cadet_id, 100)
        result.append(d)

    return jsonify({'error': False, 'success': True, 'applications': result})

@app.route('/api/admin/camp-applications/status', methods=['POST'])
@login_required
def update_camp_application_status():
    """Admin: select or reject a camp application."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    data = request.get_json(force=True) or {}
    appln_id = data.get('application_id')
    status = data.get('status')
    note = data.get('note', '')

    if not appln_id or status not in ['pending', 'selected', 'rejected']:
        return jsonify({'error': True, 'message': 'Application ID and a valid status are required'}), 400

    appln = CampApplication.query.get(appln_id)
    if not appln:
        return jsonify({'error': True, 'message': 'Application not found'}), 404

    appln.status = status
    if note:
        appln.note = note
    db.session.commit()

    # Trigger alert to cadet
    try:
        msg = f"Your application for '{appln.camp.title}' has been {status}."
        if status == 'selected':
            msg += " Congratulations! Please check the details in the cadet portal."
        elif note:
            msg += f" Remarks: {note}"
        send_cadet_alert(appln.cadet_id, msg, title="Camp Nomination Update")
    except Exception as e:
        print(f"Error sending camp status alert: {e}")

    return jsonify({
        'error': False,
        'success': True,
        'message': f"Cadet application status updated to {status}",
        'application': appln.to_dict()
    })


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
        is_approved=False,
        wing=wing
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
@login_required
def api_admin_all_cadets():
    """Admin: get all cadets."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
            'status': 'approved' if c.is_approved else 'pending',
            'cert_a_approved': c.cert_a_approved,
            'cert_b_approved': c.cert_b_approved,
            'wing': c.wing or 'Army'
        } for c in cadets]
    })

@app.route('/api/admin/pending-cadets', methods=['GET'])
@login_required
def api_admin_pending_cadets():
    """Admin: get all cadets pending approval."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
@login_required
def api_admin_approve_cadet():
    """Admin: approve or reject a pending cadet."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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

@app.route('/api/admin/approve-certificate', methods=['POST'])
@login_required
def api_admin_approve_certificate():
    """Admin: approve or revoke a cadet's certificate."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    data = request.get_json(force=True) or {}
    cadet_id = data.get('cadet_id')
    cert_type = data.get('cert_type') # 'A' or 'B'
    approved = data.get('approved') # True or False

    cadet = User.query.get(cadet_id)
    if not cadet or cadet.is_admin:
        return jsonify({'error': True, 'message': 'Cadet not found'}), 404

    if cert_type == 'A':
        cadet.cert_a_approved = bool(approved)
    elif cert_type == 'B':
        cadet.cert_b_approved = bool(approved)
    else:
        return jsonify({'error': True, 'message': 'Invalid certificate type'}), 400

    db.session.commit()
    return jsonify({
        'error': False,
        'success': True,
        'message': f"Certificate {cert_type} {'approved' if approved else 'revoked'} successfully"
    })

@app.route('/api/students/<int:id>', methods=['DELETE'])
@login_required
def api_delete_student(id):
    """Admin: permanently delete a cadet account."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    contacts = Contact.query.order_by(Contact.created_at.desc()).all()
    return jsonify({'error': False, 'success': True, 'contacts': [c.to_dict() for c in contacts]})

@app.route('/api/contact/<int:id>/read', methods=['PATCH'])
@login_required
def api_contact_read(id):
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    contact = Contact.query.get_or_404(id)
    contact.is_read = True
    db.session.commit()
    return jsonify({'error': False, 'success': True})

@app.route('/api/contact/<int:id>', methods=['DELETE'])
@login_required
def api_contact_delete(id):
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
        data = request.get_json(silent=True) or {}
        cadet = request.form.get('cadet') or request.form.get('ach-cadet') or data.get('cadet') or data.get('ach-cadet') or ''
        award = request.form.get('award') or request.form.get('ach-award') or data.get('award') or data.get('ach-award') or ''
        ach_type = request.form.get('type') or request.form.get('ach-type') or data.get('type') or data.get('ach-type') or ''
        ach_date = request.form.get('date') or request.form.get('ach-date') or data.get('date') or data.get('ach-date') or ''
        
        cadet = cadet.strip()
        award = award.strip()
        
        if not cadet or not award:
            return jsonify({'error': True, 'message': 'Cadet name and award are required'}), 400
        achievement = Achievement(
            cadet=cadet, award=award,
            achievement_type=ach_type,
            date=ach_date or utcnow_helper().strftime('%Y-%m-%d')
        )
        db.session.add(achievement)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'achievement': achievement.to_dict()}), 201

    achievements = Achievement.query.order_by(Achievement.created_at.desc()).all()
    return jsonify({'error': False, 'success': True, 'achievements': [a.to_dict() for a in achievements]})

@app.route('/api/achievements/<int:id>', methods=['DELETE'])
@login_required
def api_delete_achievement(id):
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    achievement = Achievement.query.get_or_404(id)
    db.session.delete(achievement)
    db.session.commit()
    return jsonify({'error': False, 'success': True})


# =============================================================================
# DASHBOARD STATS API (real data)
# =============================================================================

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def api_dashboard_stats():
    """Returns real-time stats for the admin dashboard."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
@login_required
def api_attendance_admin_summary():
    """Alias for /api/attendance/daily — used by old admin dashboard JS."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
@login_required
def api_attendance_admin_mark():
    """Mark a single cadet present/absent — used by admin dashboard toggle buttons."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
        existing.marked_at = utcnow_helper()
    else:
        record = Attendance(cadet_id=cadet_id, date=target_date,
                            status=status, marked_by_admin=True)
        db.session.add(record)
    db.session.commit()
    return jsonify({'error': False, 'success': True,
                    'message': f'{cadet.username} marked {status}'})


@app.route('/api/attendance/admin-mark-all', methods=['POST'])
@login_required
def api_attendance_admin_mark_all():
    """Mark ALL approved cadets as present for a date — used by Mark All Present button."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
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
            existing.marked_at = utcnow_helper()
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


# =============================================================================
# PWA & SMS ALERT SYSTEM API
# =============================================================================

@app.route('/api/notifications/subscribe', methods=['POST'])
@login_required
def api_notifications_subscribe():
    """Cadet: register/save browser PushSubscription for PWA push notifications."""
    data = request.get_json(force=True) or {}
    endpoint = data.get('endpoint')
    keys = data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({'error': True, 'message': 'Missing subscription details'}), 400

    # Avoid duplicate subscriptions for the same endpoint
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        new_sub = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth
        )
        db.session.add(new_sub)
    
    try:
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'Subscription successfully registered'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': f'Database error: {e}'}), 500


@app.route('/api/notifications/test-send', methods=['POST'])
@login_required
def api_notifications_test_send():
    """Cadet: dispatch a real-time test notification to confirm integration works."""
    success = send_cadet_alert(
        user_id=current_user.id,
        message="Your real-time notification integration is active and working perfectly! 🚀",
        title="PWA Connection Success",
        channels=['push'],
        category='success'
    )
    if success:
        return jsonify({'error': False, 'success': True, 'message': 'Test notification triggered successfully!'})
    return jsonify({'error': True, 'message': 'Failed to trigger test notification'}), 500


@app.route('/api/notifications/poll', methods=['GET'])
@login_required
def api_notifications_poll():
    """Cadet: poll recent notifications/alerts sent to this user."""
    alerts = SmsAlert.query.filter_by(user_id=current_user.id).order_by(SmsAlert.sent_at.desc()).limit(10).all()
    return jsonify({
        'error': False,
        'success': True,
        'alerts': [a.to_dict() for a in alerts]
    })


@app.route('/api/admin/alerts/history', methods=['GET'])
@login_required
def api_admin_alerts_history():
    """Admin: retrieve sent alert history log with optional filters."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
    
    # Optional filters from query parameters
    filter_category = request.args.get('category', '').strip()
    filter_status = request.args.get('status', '').strip()
    
    query = SmsAlert.query
    if filter_category:
        query = query.filter_by(category=filter_category)
    if filter_status:
        query = query.filter_by(status=filter_status)
    
    alerts = query.order_by(SmsAlert.sent_at.desc()).limit(200).all()
    sub_count = PushSubscription.query.count()
    sms_count = SmsAlert.query.count()
    twilio_status = "Active" if (TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER) else "Simulated/Logs"

    return jsonify({
        'error': False,
        'success': True,
        'alerts': [a.to_dict() for a in alerts],
        'stats': {
            'push_subscribers': sub_count,
            'sent_alerts_count': sms_count,
            'twilio_status': twilio_status
        }
    })


@app.route('/api/admin/alerts/send-broadcast', methods=['POST'])
@login_required
def api_admin_alerts_send_broadcast():
    """Admin: trigger custom broadcast (SMS/Push) to selected cadets."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    data = request.get_json(force=True) or {}
    title = data.get('title', 'NCC Announcement')
    message = data.get('message')
    channels = data.get('channels', ['push', 'sms']) # sms, push, or both
    target = data.get('target', 'all')  # all, year_1, year_2, year_3, army, navy, air, individual
    
    # Tier 1 & 2 fields
    requires_ack = data.get('requires_acknowledgement', False)
    email_ch = data.get('email_channel', False)
    whatsapp_ch = data.get('whatsapp_channel', False)
    is_recurring_flag = data.get('is_recurring', False)
    recurrence_type_val = data.get('recurrence_type', None)
    recurrence_interval_val = int(data.get('recurrence_interval', 1) or 1)
    reminder_hours_val = data.get('reminder_hours', None)
    cadet_id = data.get('cadet_id')
    
    # Advanced scheduling and categorization
    scheduled_at_str = data.get('scheduled_at')
    category = data.get('category', 'info') # info, warning, success, danger

    if not message:
        return jsonify({'error': True, 'message': 'Message body is required'}), 400

    scheduled_at = None
    if scheduled_at_str:
        try:
            clean_str = scheduled_at_str.replace('Z', '')
            if '.' in clean_str:
                clean_str = clean_str.split('.')[0]
            # Convert ISO datetime format
            scheduled_at = datetime.strptime(clean_str, '%Y-%m-%dT%H:%M:%S')
        except Exception as parse_err:
            print(f"Error parsing scheduled date: {parse_err}")
            return jsonify({'error': True, 'message': 'Invalid scheduled date format. Use ISO format.'}), 400

    # Build targets based on group selection
    users_query = User.query.filter_by(is_admin=False, is_approved=True)

    if target == 'individual':
        if not cadet_id:
            return jsonify({'error': True, 'message': 'Cadet ID is required for individual target'}), 400
        users_query = users_query.filter_by(id=cadet_id)
    elif target.startswith('year_'):
        year_val = target.split('_')[1]  # '1', '2', '3'
        users_query = users_query.filter(User.year.like(f'%{year_val}%'))
    elif target == 'army':
        users_query = users_query.filter(User.wing.ilike('%army%'))
    elif target == 'navy':
        users_query = users_query.filter(User.wing.ilike('%navy%'))
    elif target == 'air':
        users_query = users_query.filter(User.wing.ilike('%air%'))

    recipients = users_query.all()
    if not recipients:
        return jsonify({'error': True, 'message': 'No matching cadets found for selected criteria'}), 404

    count = 0
    for r in recipients:
        try:
            # Determine phone
            phone_val = r.phone_number or 'In-App'
            if phone_val != 'In-App' and not phone_val.startswith('+'):
                if len(phone_val) == 10 and phone_val.isdigit():
                    phone_val = '+91' + phone_val

            # Simulate email channel
            if email_ch and r.email:
                try:
                    log_path = os.path.join('instance', 'email_logs.txt')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{utcnow_helper().isoformat()}] TO: {r.email} | SUBJ: [{title}] | BODY: {message}\n")
                except Exception:
                    pass

            # Simulate WhatsApp channel
            if whatsapp_ch and r.phone_number:
                try:
                    log_path = os.path.join('instance', 'whatsapp_logs.txt')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{utcnow_helper().isoformat()}] TO: {r.phone_number} | WA MSG: [{title}] {message}\n")
                except Exception:
                    pass

            # Compute next recurrence
            next_rec = None
            if is_recurring_flag and recurrence_type_val and not scheduled_at:
                from datetime import timedelta
                now_t = utcnow_helper()
                if recurrence_type_val == 'daily':
                    next_rec = now_t + timedelta(days=recurrence_interval_val)
                elif recurrence_type_val == 'weekly':
                    next_rec = now_t + timedelta(weeks=recurrence_interval_val)
                elif recurrence_type_val == 'monthly':
                    next_rec = now_t + timedelta(days=30 * recurrence_interval_val)

            # Create alert record with all new Tier 1/2 fields
            alert_log = SmsAlert(
                user_id=r.id,
                receiver_phone=phone_val,
                message_title=title,
                message_body=message,
                status='scheduled' if scheduled_at else 'simulated',
                scheduled_at=scheduled_at,
                category=category,
                target_group=target,
                requires_acknowledgement=bool(requires_ack),
                email_channel=bool(email_ch),
                whatsapp_channel=bool(whatsapp_ch),
                is_recurring=bool(is_recurring_flag),
                recurrence_type=recurrence_type_val,
                recurrence_interval=recurrence_interval_val,
                next_recurrence_at=next_rec,
                reminder_hours=int(reminder_hours_val) if reminder_hours_val else None
            )
            db.session.add(alert_log)
            count += 1
        except Exception as ex:
            print(f"[BROADCAST] Failed to create alert for {r.username}: {ex}")

    try:
        db.session.commit()
    except Exception as db_err:
        db.session.rollback()
        return jsonify({'error': True, 'message': f'Database error: {db_err}'}), 500

    msg_word = "scheduled" if scheduled_at else "sent"
    return jsonify({
        'error': False,
        'success': True,
        'message': f'Broadcast successfully {msg_word} to {count} cadet(s)',
        'count': count
    })






@app.route('/api/cadet/my-alerts', methods=['GET'])
@login_required
def api_cadet_my_alerts():
    """Cadet: fetch their own received alert notifications with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    filter_cat = request.args.get('category', '')  # optional filter by category
    unread_only = request.args.get('unread', 'false').lower() == 'true'

    query = SmsAlert.query.filter_by(user_id=current_user.id).filter(
        SmsAlert.status.in_(['sent', 'simulated'])
    )
    if filter_cat:
        query = query.filter_by(category=filter_cat)
    if unread_only:
        query = query.filter_by(is_read=False)

    total = query.count()
    alerts = query.order_by(SmsAlert.sent_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    unread_count = SmsAlert.query.filter_by(
        user_id=current_user.id, is_read=False
    ).filter(SmsAlert.status.in_(['sent', 'simulated'])).count()

    return jsonify({
        'error': False,
        'alerts': [a.to_dict() for a in alerts],
        'total': total,
        'page': page,
        'per_page': per_page,
        'unread_count': unread_count
    })


@app.route('/api/cadet/alerts/mark-read/<int:alert_id>', methods=['POST'])
@login_required
def api_cadet_alert_mark_read(alert_id):
    """Cadet: mark a single alert as read."""
    alert = SmsAlert.query.filter_by(id=alert_id, user_id=current_user.id).first()
    if not alert:
        return jsonify({'error': True, 'message': 'Alert not found'}), 404
    alert.is_read = True
    try:
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'Alert marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/api/cadet/alerts/mark-all-read', methods=['POST'])
@login_required
def api_cadet_alerts_mark_all_read():
    """Cadet: mark all their unread alerts as read."""
    try:
        SmsAlert.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'All alerts marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/api/admin/alerts/cancel/<int:alert_id>', methods=['POST', 'DELETE'])
@login_required
def api_admin_alerts_cancel(alert_id):
    """Admin: cancel a scheduled alert before it gets sent."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
        
    alert = SmsAlert.query.get(alert_id)
    if not alert:
        return jsonify({'error': True, 'message': 'Scheduled alert not found'}), 404
        
    if alert.status != 'scheduled':
        return jsonify({'error': True, 'message': 'Only scheduled alerts can be cancelled'}), 400
        
    try:
        db.session.delete(alert)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'Scheduled alert successfully cancelled!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': f'Database error: {e}'}), 500


@app.route('/api/admin/alerts/delete/<int:alert_id>', methods=['POST', 'DELETE'])
@login_required
def api_admin_alerts_delete(alert_id):
    """Admin: delete a notification alert from the log/history completely."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403
        
    alert = SmsAlert.query.get(alert_id)
    if not alert:
        return jsonify({'error': True, 'message': 'Alert record not found'}), 404
        
    try:
        db.session.delete(alert)
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'Alert successfully deleted!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': f'Database error: {e}'}), 500



# =============================================================================
# ALERT MANAGER — TIER 1 & 2 NEW API ENDPOINTS
# =============================================================================

@app.route('/api/admin/alerts/send-emergency', methods=['POST'])
@login_required
def api_admin_send_emergency():
    """Admin: Emergency SOS — blast all approved cadets immediately via all channels."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    data = request.get_json(force=True) or {}
    message = data.get('message', 'EMERGENCY: Urgent action required. Report to ANO immediately.')
    title = data.get('title', '🚨 EMERGENCY ALERT')

    cadets = User.query.filter_by(is_admin=False, is_approved=True).all()
    if not cadets:
        return jsonify({'error': True, 'message': 'No approved cadets found'}), 404

    dispatched = 0
    for cadet in cadets:
        try:
            phone = cadet.phone_number or 'In-App'
            phone_norm = phone.strip() if phone and phone.strip() else 'In-App'
            if phone_norm != 'In-App' and not phone_norm.startswith('+'):
                if len(phone_norm) == 10 and phone_norm.isdigit():
                    phone_norm = '+91' + phone_norm
            alert_log = SmsAlert(
                user_id=cadet.id,
                receiver_phone=phone_norm,
                message_title=title,
                message_body=message,
                status='simulated',
                category='danger',
                is_emergency=True,
                target_group='all',
                requires_acknowledgement=True,
                email_channel=False,
                whatsapp_channel=False
            )
            db.session.add(alert_log)
            dispatched += 1
            print(f"[EMERGENCY] SOS alert dispatched to cadet: {cadet.username}")
        except Exception as e:
            print(f"[EMERGENCY] Failed to alert {cadet.username}: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': f'Database error: {e}'}), 500

    return jsonify({
        'error': False,
        'success': True,
        'message': f'🚨 Emergency SOS dispatched to {dispatched} cadet(s)!',
        'dispatched_to': dispatched
    })


@app.route('/api/cadet/alerts/acknowledge/<int:alert_id>', methods=['POST'])
@login_required
def api_cadet_alert_acknowledge(alert_id):
    """Cadet: acknowledge an action-required alert."""
    alert = SmsAlert.query.filter_by(id=alert_id, user_id=current_user.id).first()
    if not alert:
        return jsonify({'error': True, 'message': 'Alert not found'}), 404
    if not alert.requires_acknowledgement:
        return jsonify({'error': True, 'message': 'This alert does not require acknowledgement'}), 400

    try:
        alert.is_acknowledged = True
        alert.acknowledged_at = utcnow_helper()
        alert.is_read = True
        db.session.commit()
        return jsonify({'error': False, 'success': True, 'message': 'Alert acknowledged successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/api/admin/alerts/read-receipts', methods=['GET'])
@login_required
def api_admin_alert_read_receipts():
    """Admin: get read receipt stats across all alerts or for a specific alert."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    alert_id = request.args.get('alert_id', type=int)

    if alert_id:
        # Per-alert read receipts
        alerts = SmsAlert.query.filter_by(id=alert_id).all()
        if not alerts:
            return jsonify({'error': True, 'message': 'Alert not found'}), 404
        receipts = []
        for a in alerts:
            receipts.append({
                'cadet_name': a.user.username if a.user else 'Unknown',
                'cadet_id': a.user_id,
                'is_read': a.is_read,
                'is_acknowledged': a.is_acknowledged or False,
                'acknowledged_at': a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                'phone': a.receiver_phone
            })
        return jsonify({'error': False, 'receipts': receipts})

    # Aggregate stats per message_title
    from sqlalchemy import func
    stats = db.session.query(
        SmsAlert.message_title,
        SmsAlert.category,
        SmsAlert.sent_at,
        func.count(SmsAlert.id).label('total'),
        func.sum(db.cast(SmsAlert.is_read, db.Integer)).label('read_count'),
        func.sum(db.cast(SmsAlert.is_acknowledged, db.Integer)).label('ack_count'),
        func.sum(db.case((SmsAlert.requires_acknowledgement == True, 1), else_=0)).label('requires_ack')
    ).filter(
        SmsAlert.user_id.isnot(None)
    ).group_by(
        SmsAlert.message_title, SmsAlert.category, SmsAlert.sent_at
    ).order_by(SmsAlert.sent_at.desc()).limit(20).all()

    result = []
    for row in stats:
        total = row.total or 1
        read = int(row.read_count or 0)
        ack = int(row.ack_count or 0)
        result.append({
            'title': row.message_title or 'NCC Announcement',
            'category': row.category or 'info',
            'sent_at': row.sent_at.isoformat() if row.sent_at else None,
            'total_recipients': total,
            'read_count': read,
            'unread_count': total - read,
            'read_rate': round((read / total) * 100),
            'ack_count': ack,
            'requires_ack': int(row.requires_ack or 0)
        })

    return jsonify({'error': False, 'receipts': result})


@app.route('/api/admin/alerts/resend-unread', methods=['POST'])
@login_required
def api_admin_resend_unread():
    """Admin: resend an alert to all cadets who haven't read it yet."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    data = request.get_json(force=True) or {}
    title = data.get('title')
    message = data.get('message')
    category = data.get('category', 'info')

    if not title or not message:
        return jsonify({'error': True, 'message': 'title and message are required'}), 400

    # Find unread alerts with this title
    unread_alerts = SmsAlert.query.filter_by(
        message_title=title, is_read=False
    ).filter(SmsAlert.user_id.isnot(None)).all()

    if not unread_alerts:
        return jsonify({'error': False, 'message': 'No unread recipients found for this alert!', 'count': 0})

    resent = 0
    for alert in unread_alerts:
        try:
            # Create a new reminder alert for each unread cadet
            new_alert = SmsAlert(
                user_id=alert.user_id,
                receiver_phone=alert.receiver_phone,
                message_title=f'[Reminder] {title}',
                message_body=message,
                status='simulated',
                category=category,
                target_group=alert.target_group,
                requires_acknowledgement=alert.requires_acknowledgement
            )
            db.session.add(new_alert)
            resent += 1
        except Exception as e:
            print(f"Resend error for user {alert.user_id}: {e}")

    db.session.commit()
    return jsonify({
        'error': False,
        'success': True,
        'message': f'Reminder sent to {resent} unread cadet(s)!',
        'count': resent
    })


@app.route('/api/admin/alerts/remind-individual/<int:alert_id>', methods=['POST'])
@login_required
def api_admin_remind_individual(alert_id):
    """Admin: resend a reminder to a specific cadet who hasn't read/acknowledged a broadcast alert yet."""
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Admin privileges required'}), 403

    alert = SmsAlert.query.get(alert_id)
    if not alert:
        return jsonify({'error': True, 'message': 'Alert not found'}), 404

    if alert.is_read and (not alert.requires_acknowledgement or alert.is_acknowledged):
        return jsonify({'error': True, 'message': 'Cadet has already read or acknowledged this alert!'}), 400

    try:
        new_alert = SmsAlert(
            user_id=alert.user_id,
            receiver_phone=alert.receiver_phone,
            message_title=f'[Reminder] {alert.message_title}',
            message_body=alert.message_body,
            status='simulated',
            category=alert.category,
            target_group='individual',
            requires_acknowledgement=alert.requires_acknowledgement
        )
        db.session.add(new_alert)
        db.session.commit()
        return jsonify({
            'error': False,
            'success': True,
            'message': f'Reminder sent successfully to {alert.user.username if alert.user else alert.receiver_phone}!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': True, 'message': str(e)}), 500


import threading
import time

def start_alert_scheduler(app_instance):
    def run_scheduler():
        time.sleep(3) # Wait for database initialization
        while True:
            with app_instance.app_context():
                try:
                    now = utcnow_helper()
                    pending = SmsAlert.query.filter(
                        SmsAlert.status == 'scheduled',
                        SmsAlert.scheduled_at <= now
                    ).all()
                    
                    for alert in pending:
                        # Mark as processing
                        alert.status = 'processing'
                        db.session.commit()
                        
                        channels = []
                        if alert.receiver_phone == 'PWA Push':
                            channels = ['push']
                        elif alert.receiver_phone.startswith('+'):
                            channels = ['sms']
                        else:
                            channels = ['push', 'sms']
                            
                        send_cadet_alert(
                            user_id=alert.user_id,
                            message=alert.message_body,
                            title='NCC Scheduled Update',
                            channels=channels,
                            scheduled_at=None,
                            category=alert.category,
                            existing_alert_id=alert.id
                        )
                        print(f"[DAEMON] Dispatched scheduled alert ID {alert.id} successfully")
                except Exception as scheduler_err:
                    print(f"[DAEMON ERROR] Scheduled alert check-in failed: {scheduler_err}")
            time.sleep(10)

    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    print("[DAEMON STARTED] Background scheduled alert checker active!")

# =============================================================================
# LEAVE REQUEST SYSTEM
# =============================================================================

# =============================================================================
# BULK CADET ACTIONS
# =============================================================================

@app.route('/api/admin/cadets/bulk-approve', methods=['POST'])
@login_required
def api_admin_bulk_approve():
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Unauthorized'}), 403
        
    data = request.get_json(force=True) or {}
    user_ids = data.get('user_ids', [])
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({'error': True, 'message': 'Invalid user IDs list'}), 400
        
    users = User.query.filter(User.id.in_(user_ids), User.is_admin == False).all()
    count = 0
    for u in users:
        if not u.is_approved:
            u.is_approved = True
            count += 1
            send_cadet_alert(u.id, "Congratulations! Your cadet enrollment application has been officially approved by the ANO office. Welcome to the platoon!", title="Enrollment Approved", category='success')
            
    db.session.commit()
    return jsonify({'error': False, 'message': f'Successfully approved {count} cadets!'})

@app.route('/api/admin/cadets/bulk-delete', methods=['POST'])
@login_required
def api_admin_bulk_delete():
    if not current_user.is_admin:
        return jsonify({'error': True, 'message': 'Unauthorized'}), 403
        
    data = request.get_json(force=True) or {}
    user_ids = data.get('user_ids', [])
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({'error': True, 'message': 'Invalid user IDs list'}), 400
        
    users = User.query.filter(User.id.in_(user_ids), User.is_admin == False).all()
    count = 0
    for u in users:
        db.session.delete(u)
        count += 1
        
    db.session.commit()
    return jsonify({'error': False, 'message': f'Successfully permanently deleted {count} cadet records!'})

# Start the background daemon scheduler
start_alert_scheduler(app)


# Run the app
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
