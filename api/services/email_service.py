"""Email service for sending notifications.

Supports both SMTP and console logging modes.
Configure via environment variables:
  SMTP_HOST - SMTP server hostname
  SMTP_PORT - SMTP port (default: 587)
  SMTP_USER - SMTP username
  SMTP_PASSWORD - SMTP password
  SMTP_FROM_EMAIL - Sender email address
  SMTP_FROM_NAME - Sender display name
  APP_BASE_URL - Base URL for the app (for links)

If SMTP_HOST is not set, emails are logged to console instead of sent.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER")
        self.smtp_password = os.environ.get("SMTP_PASSWORD")
        self.from_email = os.environ.get("SMTP_FROM_EMAIL", "noreply@example.com")
        self.from_name = os.environ.get("SMTP_FROM_NAME", "Orchestrator")
        self.app_base_url = os.environ.get("APP_BASE_URL", "http://localhost:5173")

    @property
    def is_configured(self) -> bool:
        """Check if SMTP is configured."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            # Log instead of sending
            logger.info(
                f"[EMAIL - Not Configured] To: {to_email}\n"
                f"Subject: {subject}\n"
                f"Body: {body_text}"
            )
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Add plain text part
            msg.attach(MIMEText(body_text, "plain"))

            # Add HTML part if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_workspace_invite(
        self,
        to_email: str,
        workspace_name: str,
        invite_token: str,
        inviter_name: Optional[str] = None,
    ) -> bool:
        """Send workspace invitation email.

        Args:
            to_email: Invitee email address
            workspace_name: Name of the workspace
            invite_token: Unique invite token
            inviter_name: Name of person who sent invite

        Returns:
            True if sent successfully
        """
        invite_url = f"{self.app_base_url}/accept-invite/{invite_token}"

        inviter_text = f" by {inviter_name}" if inviter_name else ""

        subject = f"You've been invited to join {workspace_name}"

        body_text = f"""
You've been invited{inviter_text} to join the workspace "{workspace_name}".

Click the link below to accept the invitation:
{invite_url}

If you don't have an account yet, you'll be prompted to create one.

This invitation will expire in 7 days.

---
If you didn't expect this invitation, you can ignore this email.
"""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    .button {{ display: inline-block; padding: 12px 24px; background: #f59e0b; color: #000; text-decoration: none; border-radius: 6px; font-weight: 600; }}
    .footer {{ margin-top: 32px; color: #666; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <h2>You've been invited to {workspace_name}</h2>
    <p>You've been invited{inviter_text} to collaborate on the workspace <strong>{workspace_name}</strong>.</p>
    <p>Click the button below to accept the invitation:</p>
    <p style="margin: 24px 0;">
      <a href="{invite_url}" class="button">Accept Invitation</a>
    </p>
    <p>Or copy and paste this link: <a href="{invite_url}">{invite_url}</a></p>
    <p>This invitation will expire in 7 days.</p>
    <div class="footer">
      <p>If you didn't expect this invitation, you can ignore this email.</p>
    </div>
  </div>
</body>
</html>
"""

        return self.send_email(to_email, subject, body_text, body_html)

    def send_password_reset(
        self,
        to_email: str,
        reset_token: str,
    ) -> bool:
        """Send password reset email.

        Args:
            to_email: User's email address
            reset_token: Unique reset token

        Returns:
            True if sent successfully
        """
        reset_url = f"{self.app_base_url}/auth/reset-password?token={reset_token}"

        subject = "Reset your password"

        body_text = f"""
You requested a password reset for your account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this password reset, you can ignore this email.
Your password will not be changed.

---
If you have any questions, please contact support.
"""

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    .button {{ display: inline-block; padding: 12px 24px; background: #3b82f6; color: #fff; text-decoration: none; border-radius: 6px; font-weight: 600; }}
    .footer {{ margin-top: 32px; color: #666; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <h2>Reset your password</h2>
    <p>You requested a password reset for your account.</p>
    <p>Click the button below to reset your password:</p>
    <p style="margin: 24px 0;">
      <a href="{reset_url}" class="button">Reset Password</a>
    </p>
    <p>Or copy and paste this link: <a href="{reset_url}">{reset_url}</a></p>
    <p>This link will expire in 1 hour.</p>
    <div class="footer">
      <p>If you didn't request this password reset, you can ignore this email.</p>
      <p>Your password will not be changed.</p>
    </div>
  </div>
</body>
</html>
"""

        return self.send_email(to_email, subject, body_text, body_html)


# Global instance
email_service = EmailService()
