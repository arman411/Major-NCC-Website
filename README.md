# NCC Unit – Govt. Polytechnic Hamirpur (HP)
## Project Structure

```
Major NCC Website/
├── backend/               ← Flask REST API (Python)
│   ├── app.py             ← Main API server (run this)
│   ├── models.py          ← SQLAlchemy database models
│   ├── config.py          ← Dev / Prod configuration
│   ├── seed.py            ← Populate DB with sample data
│   ├── requirements.txt   ← Python dependencies
│   ├── ncc_database.db    ← SQLite DB (auto-created on first run)
│   └── uploads/           ← Uploaded photos & files
│
└── frontend/              ← Static HTML/CSS/JS website
    ├── index.html         ← Home page
    ├── css/style.css
    ├── js/main.js
    ├── images/
    └── pages/
        ├── enrollment.html   ← Submits to POST /api/students/enroll
        ├── notices.html      ← Fetches from GET  /api/notices
        ├── gallery.html
        ├── login.html
        ├── about.html
        └── …
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
cd "e:\Major NCC Website\backend"
pip install -r requirements.txt
```

### 2. Seed the Database (first time only)

```powershell
python seed.py
```

Output will show:
```
✅  Admin user created  –  admin@ncc-gph.ac.in  /  NCC@Admin2025
✅  6 notices seeded.
✅  4 gallery items seeded.
✅  4 camps seeded.
✅  5 achievements seeded.
🎉  Database seeding completed successfully!
```

### 3. Run the Backend

```powershell
python app.py
```

> 🚀  NCC Backend API starting on **http://127.0.0.1:5000**

### 4. Open the Frontend

Open `frontend/index.html` in your browser (double-click or use Live Server).

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/auth/login` | Admin login | Public |
| `POST` | `/api/auth/signup` | Register user | Public |
| `GET`  | `/api/auth/me` | Current user info | Public |
| `POST` | `/api/students/enroll` | Submit enrollment form | **Public** |
| `GET`  | `/api/students` | List all students | Admin |
| `GET`  | `/api/students/<id>` | Get student details | Admin |
| `PATCH`| `/api/students/<id>/status` | Approve/reject cadet | Admin |
| `DELETE` | `/api/students/<id>` | Delete student record | Admin |
| `GET`  | `/api/notices` | List all notices | Public |
| `POST` | `/api/notices` | Create notice | Admin |
| `DELETE` | `/api/notices/<id>` | Delete notice | Admin |
| `GET`  | `/api/gallery` | List gallery items | Public |
| `POST` | `/api/gallery` | Upload gallery item | Admin |
| `GET`  | `/api/camps` | List camps | Public |
| `POST` | `/api/camps` | Create camp | Admin |
| `GET`  | `/api/achievements` | List achievements | Public |
| `POST` | `/api/achievements` | Add achievement | Admin |
| `POST` | `/api/contact` | Submit contact message | Public |
| `GET`  | `/api/contact` | Read all messages | Admin |
| `GET`  | `/api/dashboard/stats` | Dashboard statistics | Admin |

---

## 🗃️ Database Tables

| Table | Key Fields |
|-------|-----------|
| `students` | roll_no, name, dob, gender, phone, email, branch, year, ncc_wing, status (pending/approved/rejected) |
| `users` | username, email, password_hash, is_admin |
| `notices` | title, category, description, issued_by, deadline, is_new |
| `gallery_items` | title, category, image_path |
| `camps` | name, location, camp_type, start_date, end_date |
| `achievements` | cadet_name, title, year, level |
| `contact_messages` | name, email, subject, message, is_read |

---

## 🔑 Default Admin Credentials

| Field | Value |
|-------|-------|
| Email | `admin@ncc-gph.ac.in` |
| Password | `NCC@Admin2025` |

> ⚠️ **Change this password immediately in production!**
