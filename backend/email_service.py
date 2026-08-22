import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Configure via environment variables ───────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")        # e.g. yourapp@gmail.com
SMTP_PASS = os.getenv("SMTP_PASS", "")        # Gmail App Password
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SMTP_USER)


def _send(to: str, subject: str, html: str):
    """Send an email. Silently logs on failure so the app never crashes."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[Email] SMTP not configured. Would have sent to {to}: {subject}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"PulseNet-GIS <{SMTP_USER}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to, msg.as_string())
        print(f"[Email] Sent to {to}: {subject}")
    except Exception as e:
        print(f"[Email] Failed to send to {to}: {e}")


def notify_admin_new_registration(role: str, name: str, contact_email: str, request_id: int):
    subject = f"[PulseNet] New {role} Registration Pending Approval — {name}"
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">
      <div style="background:#1e3a8a;padding:24px 32px">
        <h1 style="color:white;margin:0;font-size:20px">PulseNet-GIS</h1>
        <p style="color:#bfdbfe;margin:4px 0 0">Admin Notification</p>
      </div>
      <div style="padding:32px">
        <h2 style="color:#1e3a8a;margin-top:0">New Registration Pending Approval</h2>
        <table style="width:100%;border-collapse:collapse">
          <tr><td style="padding:8px;color:#6b7280;font-size:14px">Type</td><td style="padding:8px;font-weight:600">{role}</td></tr>
          <tr style="background:#f9fafb"><td style="padding:8px;color:#6b7280;font-size:14px">Name</td><td style="padding:8px;font-weight:600">{name}</td></tr>
          <tr><td style="padding:8px;color:#6b7280;font-size:14px">Email</td><td style="padding:8px">{contact_email}</td></tr>
          <tr style="background:#f9fafb"><td style="padding:8px;color:#6b7280;font-size:14px">Request ID</td><td style="padding:8px">#{request_id}</td></tr>
        </table>
        <div style="margin-top:24px;text-align:center">
          <a href="http://localhost:8000/admin/" style="background:#1e3a8a;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block">
            Review on Admin Portal
          </a>
        </div>
      </div>
    </div>"""
    _send(ADMIN_EMAIL, subject, html)


def send_approval_credentials(to_email: str, name: str, role: str, login_email: str):
    role_label = {"PHC": "PHC / Clinic", "HOSPITAL": "Hospital", "AMBULANCE": "Ambulance Driver"}.get(role, role)
    subject = f"[PulseNet] Your Registration is Approved — {name}"
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">
      <div style="background:#1e3a8a;padding:24px 32px">
        <h1 style="color:white;margin:0;font-size:20px">PulseNet-GIS</h1>
        <p style="color:#bfdbfe;margin:4px 0 0">Registration Approved</p>
      </div>
      <div style="padding:32px">
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin-bottom:24px">
          <h2 style="color:#16a34a;margin:0 0 4px">Congratulations! Your registration has been approved.</h2>
          <p style="color:#166534;margin:0;font-size:14px">You can now log in to PulseNet-GIS as a {role_label}.</p>
        </div>
        <h3 style="color:#1e3a8a">Your Login Credentials</h3>
        <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
          <tr style="background:#f9fafb"><td style="padding:12px 16px;color:#6b7280;font-size:14px;width:40%">Login URL</td><td style="padding:12px 16px"><a href="http://localhost:8000/login.html">http://localhost:8000/login.html</a></td></tr>
          <tr><td style="padding:12px 16px;color:#6b7280;font-size:14px">Email / Username</td><td style="padding:12px 16px;font-weight:600;color:#1e3a8a">{login_email}</td></tr>
          <tr style="background:#f9fafb"><td style="padding:12px 16px;color:#6b7280;font-size:14px">Password</td><td style="padding:12px 16px;font-weight:600;color:#1e3a8a;font-size:14px">The password you entered during registration</td></tr>
        </table>
      </div>
    </div>"""
    _send(to_email, subject, html)


def send_rejection_email(to_email: str, name: str, role: str, reason: str = ""):
    subject = f"[PulseNet] Registration Update — {name}"
    reason_block = f"<p style='color:#374151;font-size:14px'><strong>Reason:</strong> {reason}</p>" if reason else ""
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">
      <div style="background:#1e3a8a;padding:24px 32px">
        <h1 style="color:white;margin:0;font-size:20px">PulseNet-GIS</h1>
      </div>
      <div style="padding:32px">
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:16px;margin-bottom:24px">
          <h2 style="color:#dc2626;margin:0 0 4px">Registration Not Approved</h2>
          <p style="color:#7f1d1d;margin:0;font-size:14px">Your {role} registration for <strong>{name}</strong> could not be approved at this time.</p>
        </div>
        {reason_block}
        <p style="color:#6b7280;font-size:14px">If you believe this is an error, please contact the PulseNet-GIS administration team.</p>
      </div>
    </div>"""
    _send(to_email, subject, html)
