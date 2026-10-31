"""Timed jobs for weddings. Registered in common/jobs.py."""
import logging

from django.db import close_old_connections, connection

from weddings.eventday import mark_late_arrivals

log = logging.getLogger(__name__)


def _tidy_connections() -> None:
    """Close stale database connections, but never one that is inside a transaction (like a test)."""
    if not connection.in_atomic_block:
        close_old_connections()


def mark_late_vendors() -> int:
    """Every minute: turn overdue pending check-ins into LATE and alert once for each."""
    _tidy_connections()  # the scheduler thread owns its own database connection
    try:
        sent = mark_late_arrivals()
        if sent:
            log.info("Sent %s late-vendor alert(s)", sent)
        return sent
    finally:
        _tidy_connections()
