"""
utils/email.py — Email sending utility (optional)
"""

import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "NCC GPH Hamirpur <noreply@gph.edu.in>")


def _send(to: str, subject: str, body: str):
    if not MAIL_USERNAME:
        print(f"[MAIL DISABLED] To: {to} | Subject: {subject}")
        return
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(body, "html"))
    
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM, to, msg.as_string())


async def send_otp_email(to_email: str, username: str, otp: str):
    subject = "Your NCC Login OTP"
    body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#060C1A;color:#fff;padding:40px;">
    <div style="max-width:500px;margin:auto;background:#0D2B5E;border-radius:16px;padding:32px;">
        <h2 style="color:#F1C40F;margin-bottom:8px;">🎖️ NCC GPH Hamirpur</h2>
        <p>Hello <strong>{username}</strong>,</p>
        <p>Your login OTP is:</p>
        <div style="font-size:2.5rem;font-weight:900;letter-spacing:12px;text-align:center;
                    color:#F1C40F;background:#060C1A;border-radius:12px;padding:20px;margin:20px 0;">
            {otp}
        </div>
        <p style="color:rgba(255,255,255,0.6);">This code is valid for <strong>5 minutes</strong>.</p>
        <hr style="border-color:rgba(255,255,255,0.1);margin:20px 0;">
        <p style="color:rgba(255,255,255,0.4);font-size:12px;">
            If you didn't request this, please ignore this email.
        </p>
    </div>
    </body></html>
    """
    _send(to_email, subject, body)
