import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

from backend.app.core.config import settings

log = logging.getLogger(__name__)


def send_password_reset(email: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?{urlencode({'token': token})}"
    body = (
        "Someone asked to reset the password for your AI-Finance-OS account.\n\n"
        f"Reset it here (valid for {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes):\n{link}\n\n"
        "If this wasn't you, ignore this email; your password will not change."
    )

    if settings.EMAIL_BACKEND == "log":
        if settings.ENVIRONMENT == "production":
            log.error("EMAIL_BACKEND=log in production: password reset email was not sent")
        else:
            # Development convenience only. Never enabled in production.
            log.info("password reset link (development only): %s", link)
        return

    message = EmailMessage()
    message["Subject"] = "Reset your AI-Finance-OS password"
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.get_secret_value())
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        log.error("password reset email failed: %s", type(exc).__name__)
