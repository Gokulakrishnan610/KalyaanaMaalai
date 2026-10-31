"""Background jobs that run on a timer (`python manage.py run_jobs`).

To add one, write a normal function in your own app and add a line below, e.g.
    {"function": "weddings.jobs.mark_late_vendors", "minutes": 1},
    {"function": "payments.jobs.remind_due_payments", "hour": 9},
Use `minutes` for "every N minutes" or `hour` for "every day at that hour (UTC)".
"""

JOBS: list[dict] = []
