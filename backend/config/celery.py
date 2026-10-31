"""Celery runs work outside the web request: timed jobs (late vendors, payment reminders) and slow calls
(Telegram). Redis carries the messages.

    make worker       # worker + timer for development (one terminal)

The timed jobs are listed in common/jobs.py; this file turns that list into Celery's schedule.
"""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("kalyaanamaalai")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


def build_schedule() -> dict:
    from common.jobs import JOBS

    schedule = {}
    for job in JOBS:
        when = job["minutes"] * 60.0 if "minutes" in job else crontab(hour=job["hour"], minute=0)
        schedule[job["function"]] = {"task": "common.run_job", "schedule": when, "args": (job["function"],)}
    return schedule


app.conf.beat_schedule = build_schedule()
