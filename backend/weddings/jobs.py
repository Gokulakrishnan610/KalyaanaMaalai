"""Timed jobs for weddings. Registered in common/jobs.py."""
import logging

from django.db import close_old_connections

from weddings.eventday import mark_late_arrivals

log = logging.getLogger(__name__)


def mark_late_vendors() -> int:
    """Every minute: turn overdue pending check-ins into LATE and alert once for each."""
    close_old_connections()  # the scheduler thread owns its own database connection
    try:
        sent = mark_late_arrivals()
        if sent:
            log.info("Sent %s late-vendor alert(s)", sent)
        return sent
    finally:
        close_old_connections()
