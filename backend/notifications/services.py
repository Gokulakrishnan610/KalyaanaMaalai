"""Alerts: always saved for the bell icon, and sent to Telegram when it is set up.

    notify("Caterer is late at Aarav & Meera", severity="warning")
Never raises: a Telegram problem must not stop the payment or check-in that triggered the alert.
"""
import logging

import httpx
from django.conf import settings
from django.db import IntegrityError, transaction

from notifications.models import Notification

logger = logging.getLogger(__name__)

CHANNELS = ("inapp", "telegram", "both")
SEVERITIES = ("info", "warning", "critical")


def _send_telegram(message: str, severity: str):
    token, chat_id = settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID
    if settings.MOCK_EXTERNALS or not (token and chat_id):
        logger.info("[mock telegram] %s: %s", severity, message)
        return
    try:
        response = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat_id, "text": message}, timeout=5)
        response.raise_for_status()
    except Exception as error:  # noqa: BLE001 - the token is in the URL, so log only the error type
        logger.warning("Telegram message failed (%s)", type(error).__name__)


def notify(message: str, channel: str = "both", user_id: int | None = None, severity: str = "info",
           dedupe_key: str | None = None) -> Notification | None:
    """Saves a notification (for one user, or everyone when `user_id` is empty) and sends it to Telegram.

    With a `dedupe_key`, the same key is only ever saved once: a second call returns None.
    """
    if channel not in CHANNELS:
        channel = "both"
    try:
        with transaction.atomic():
            notification = Notification.objects.create(user_id=user_id, message=message, channel=channel,
                                                       severity=severity, dedupe_key=dedupe_key)
    except IntegrityError:
        return None  # already sent
    except Exception:  # noqa: BLE001
        logger.exception("Could not save a notification")
        return None
    if channel in ("telegram", "both"):
        _send_telegram(message, severity)
    return notification
