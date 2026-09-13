# NCC Portal — Deployment Guide

This guide covers deploying the NCC Portal for free using various hosting platforms.

---

## Option 1: Render (Recommended — Free Backend Hosting)

1. Go to [https://render.com](https://render.com) and sign up with GitHub
2. Click **New → Web Service**
3. Connect your GitHub repository: `arman411/Major-NCC-Website`
4. Configure:
   - **Name:** `ncc-gph-hamirpur`
   - **Root Directory:** *(leave blank — uses root)*
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Add Environment Variables:
   - `SECRET_KEY` → *(generate a random 32-char string)*
   - `ENCRYPTION_KEY` → *(generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)*
   - `FLASK_ENV` → `production`
6. Click **Create Web Service**
7. Visit your app at `https://ncc-gph-hamirpur.onrender.com`

> ⚠️ Free tier sleeps after 15 min of inactivity. Use [UptimeRobot](https://uptimerobot.com) to ping `/api/health` every 14 minutes to keep it awake.

---

## Option 2: Railway (Free $5 credit/month)

1. Go to [https://railway.app](https://railway.app) → Login with GitHub
2. Click **New Project → Deploy from GitHub Repo**
3. Select `arman411/Major-NCC-Website`
4. Railway auto-detects Python. Set **Start Command:** `gunicorn app:app`
5. Add same environment variables as above
6. Deploy!

---

## Option 3: Local LAN (Zero Cost — College Network)

Run the portal on a college computer, accessible to all devices on the same WiFi:

```powershell
cd "e:\Major NCC Website\Major NCC Website"
pip install -r requirements.txt
# Run on all network interfaces, port 80
python app.py
```

Edit `app.py` last line:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

Now accessible at `http://192.168.X.X:5000` from any device on college WiFi.

Find your IP with:
```powershell
ipconfig  # Look for IPv4 Address
```

---

## Option 4: GitHub Pages (Frontend Only — Free)

Host the static frontend on GitHub Pages:

1. Go to your repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, Folder: `/frontend`
4. Save → Your site will be live at `https://arman411.github.io/Major-NCC-Website/`

> Note: This only serves static pages. API features require a separate backend.

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|--------|
| `SECRET_KEY` | Flask session security key | `your-random-32-char-string` |
| `ENCRYPTION_KEY` | Fernet key for field encryption | Base64 encoded 32-byte key |
| `FLASK_ENV` | Environment mode | `production` or `development` |
| `MAIL_SERVER` | SMTP server | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USERNAME` | Email for sending | `your@gmail.com` |
| `MAIL_PASSWORD` | App password | Gmail App Password |
| `TWILIO_ACCOUNT_SID` | Twilio SMS account | From Twilio dashboard |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | From Twilio dashboard |
| `TWILIO_PHONE_NUMBER` | Twilio SMS number | `+1234567890` |
| `VAPID_PUBLIC_KEY` | PWA push notification key | Generated with web-push library |
| `VAPID_PRIVATE_KEY` | PWA push notification key | Generated with web-push library |

---

## SSL/HTTPS Setup

For production, always use HTTPS. Render and Railway provide automatic SSL.

For LAN deployment, use a self-signed cert:
```powershell
pip install pyopenssl
# In app.py run with SSL:
app.run(host='0.0.0.0', port=443, ssl_context='adhoc')
```

---

## Database Backup

The portal includes an automated backup system. To download a backup:
1. Login as admin
2. Go to Admin Dashboard → Settings → **Download Backup**
3. Store the `.db` file safely offline

Or use the API directly:
```bash
curl -b cookies.txt https://your-app.onrender.com/api/admin/backup -o backup.db
```

---

## Health Check

Verify the backend is running:
```
GET /api/health
→ {"status": "ok", "message": "NCC GPH Hamirpur server is running"}
```
