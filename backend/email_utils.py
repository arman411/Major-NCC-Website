import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from threading import Thread

def send_async_email(app, msg, mail_server, mail_port, mail_username, mail_password, mail_use_tls):
    """Background task to send email directly via smtplib to avoid blocking standard response."""
    with app.app_context():
        try:
            if not mail_username or not mail_password:
                print("⚠️ Mail credentials not configured. Email blocked.")
                return

            # Connect to SMTP server
            server = smtplib.SMTP(mail_server, mail_port)
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
            server.quit()
            print(f"📧 Email sent to {msg['To']}")
        except Exception as e:
            print(f"❌ Failed to send email to {msg['To']}: {str(e)}")

def send_email(subject, recipient, text_body, html_body=None):
    """Send an email asynchronously."""
    app = current_app._get_current_object()
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = app.config.get('MAIL_DEFAULT_SENDER', 'noreply@gph.edu.in')
    msg['To'] = recipient

    # Attach text body
    part1 = MIMEText(text_body, 'plain')
    msg.attach(part1)

    # Attach html body if provided
    if html_body:
        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)

    # Use Threading to avoid blocking the main execution thread
    Thread(
        target=send_async_email,
        args=(
            app, msg,
            app.config.get('MAIL_SERVER'),
            app.config.get('MAIL_PORT'),
            app.config.get('MAIL_USERNAME'),
            app.config.get('MAIL_PASSWORD'),
            app.config.get('MAIL_USE_TLS')
        )
    ).start()

def send_enrollment_confirmation(student):
    """Send to cadet when they apply."""
    subject = "NCC Enrollment Application Received"
    text = f"""Dear {student.first_name} {student.last_name},

Your application for NCC enrollment at Govt. Polytechnic Hamirpur has been successfully submitted.
Your Roll No: {student.roll_no}
NCC Wing: {student.ncc_wing}

The ANO office will review your application and contact you within 3-5 working days.

Regards,
ANO Office,
Govt. Polytechnic Hamirpur (HP)
"""
    send_email(subject, student.email, text)

def send_status_update(student):
    """Send to cadet when admin approves/rejects them."""
    if student.status == 'approved':
        subject = "Congratulations! Outstanding NCC Application Approved"
        text = f"""Dear {student.first_name},

We are pleased to inform you that your NCC enrollment application has been APPROVED.
Your Cadet No is: {student.cadet_no if student.cadet_no else 'To be assigned soon'}

Please visit the ANO office regarding your uniform and parade schedule.

Regards,
ANO Office,
Govt. Polytechnic Hamirpur (HP)
"""
    elif student.status == 'rejected':
        subject = "Update on your NCC Application"
        text = f"""Dear {student.first_name},

We regret to inform you that your application for NCC enrollment could not be accepted at this time.
Reason/Remarks: {student.remarks if student.remarks else 'Not specified'}

Regards,
ANO Office,
Govt. Polytechnic Hamirpur (HP)
"""
    else:
        return # pending, do nothing
        
    send_email(subject, student.email, text)

def send_contact_autoreply(contact_msg):
    """Auto-reply for contact form."""
    subject = "Received your message - NCC Govt. Polytechnic Hamirpur"
    text = f"""Dear {contact_msg.name},

Thank you for reaching out to us regarding "{contact_msg.subject}".
We have received your message and will get back to you across this email shortly.

Your Message:
{contact_msg.message}

Regards,
NCC Unit, Govt. Polytechnic Hamirpur
"""
    send_email(subject, contact_msg.email, text)
