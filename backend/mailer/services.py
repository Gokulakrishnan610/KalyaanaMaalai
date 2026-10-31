"""Send an email from a template:

    send("client_welcome", "priya@example.com", name="Priya", link=url)

The message is saved in EmailLog first, then handed to a Celery worker (or sent on the spot if the queue is down).
Never raises: a mail problem must not stop the conversion or payment that triggered it.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from mailer.models import EmailLog
from mailer.templates import SAMPLE, TEMPLATES

logger = logging.getLogger(__name__)
BUSINESS = "Shaandaar Events"


class _Blank(dict):
    def __missing__(self, key):
        return ""


def render(template: str, context: dict) -> tuple[str, str, str]:
    """(subject, html, plain text) for a template and its values."""
    subject_text, _ = TEMPLATES[template]
    values = {"business": BUSINESS, "site_url": settings.CUSTOMER_SITE_URL, **context}
    subject = subject_text.format_map(_Blank(values))
    html = render_to_string(f"mailer/{template}.html", {**values, "subject": subject})
    return subject, html, strip_tags(html.split("<!--text-->", 1)[-1]).strip()


def preview(template: str) -> dict:
    subject, html, text = render(template, SAMPLE)
    return {"name": template, "subject": subject, "html": html, "when": TEMPLATES[template][1]}


def send(template: str, to: str, **context) -> EmailLog | None:
    if not to:
        return None
    try:
        subject, html, text = render(template, context)
        log = EmailLog.objects.create(template=template, to=to, subject=subject, html=html, text=text)
    except Exception:  # noqa: BLE001
        logger.exception("Could not prepare the %s email", template)
        return None
    from mailer.tasks import deliver

    try:
        deliver.apply_async(args=(log.pk,), retry=False)
    except Exception:  # noqa: BLE001
        logger.warning("Background queue unavailable, sending the email directly")
        deliver_now(log.pk)
    return log


def deliver_now(log_id: int) -> None:
    log = EmailLog.objects.get(pk=log_id)
    try:
        message = EmailMultiAlternatives(log.subject, log.text, settings.DEFAULT_FROM_EMAIL, [log.to])
        message.attach_alternative(log.html, "text/html")
        message.send()
        log.status, log.sent_at, log.error = EmailLog.Status.SENT, timezone.now(), ""
    except Exception as error:  # noqa: BLE001
        log.status, log.error = EmailLog.Status.FAILED, type(error).__name__
        logger.warning("Email to %s failed (%s)", log.to, type(error).__name__)
    log.save(update_fields=["status", "sent_at", "error"])
