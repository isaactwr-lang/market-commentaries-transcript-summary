"""Gmail SMTP sender with BCC — ported from ai-momentum/weekly-market-recap."""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(subject: str, html: str) -> None:
    sender   = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    raw      = os.getenv("RECIPIENT_EMAIL") or sender
    recipients = [r.strip() for r in raw.split(",") if r.strip()]

    if not sender or not password:
        logger.error("GMAIL_USER / GMAIL_APP_PASSWORD not set — skipping send")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = ""   # blank To — all via BCC
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
    logger.info(f"Email sent to {len(recipients)} recipient(s)")
