from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

from models import db, User, Notice, GalleryItem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_override_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ncc_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images', 'uploads')

# Initialize DB
db.init_app(app)

# Setup Login Manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create DB Tables on Startup
with app.app_context():
    db.create_all()

# --- Public Routes ---

@app.route('/')
def home():
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

        # Basic validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))
            
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'error')
            return redirect(url_for('signup'))

        # Create new user
        new_user = User(
            username=username, 
            email=email, 
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )
        # Note: Make the first user an admin manually, or via a specific root route
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('dashboard'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- Protected Routes ---

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        total_cadets = User.query.count()
        total_notices = Notice.query.count()
        recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()
        return render_template('admin-dashboard.html', 
                               cadet_count=total_cadets, 
                               notice_count=total_notices,
                               recent_notices=recent_notices)
    else:
        # For regular cadets, maybe redirect to a cadet profile or the home page
        return redirect(url_for('home'))

# Run the app
if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
