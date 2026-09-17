"""
Email-sending tool used by the Email Agent.

The original notebook imports `send_email` / `push` from a local
`messenger.py` (not shown here — it's your own SendGrid/Pushover wiring).
Production hardening applied:
- The import is guarded: if `messenger.py` isn't present or misconfigured,
  the app still boots (useful for local dev / CI) and falls back to logging
  the email instead of raising ImportError deep inside a tool call.
- Every send is wrapped so a transient email-provider failure is reported
  back to the agent (and to logs) instead of silently disappearing.
"""

from __future__ import annotations

from agents import function_tool

from .config import USE_EMAIL, logger

try:
    from messenger import push, send_email  # your existing SendGrid/Pushover module
    _MESSENGER_AVAILABLE = True
except ImportError:
    _MESSENGER_AVAILABLE = False
    logger.warning(
        "messenger module not found — emails/pushes will only be logged, not sent. "
        "Add your messenger.py (or set USE_EMAIL=false) before deploying."
    )


@function_tool
def send_email_tool(subject: str, text_body: str, html_body: str) -> str:
    """
    Send the finished report by email (or push notification as a fallback).

    Args:
        subject: The subject of the email.
        text_body: The body of the email as plain text.
        html_body: The HTML body of the email.
    """
    try:
        if USE_EMAIL and _MESSENGER_AVAILABLE:
            send_email(subject, text_body, html_body)
            logger.info("Email sent: %s", subject)
            return "Email sent successfully"

        if _MESSENGER_AVAILABLE:
            push(f"Subject: {subject}\n\n{text_body}")
            logger.info("Push notification sent: %s", subject)
            return "Push notification sent successfully"

        logger.info("[DRY RUN] Would send email — Subject: %s", subject)
        return "Email not sent (messenger not configured) — logged instead"

    except Exception as exc:
        logger.exception("Failed to send email/push for subject=%r", subject)
        return f"Failed to send: {exc}"
