from importlib import import_module

from apscheduler.schedulers.blocking import BlockingScheduler
from django.core.management.base import BaseCommand

from common.jobs import JOBS


class Command(BaseCommand):
    help = "Run the background jobs listed in common/jobs.py (keep this running in its own terminal)."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone="UTC")
        for job in JOBS:
            module_name, function_name = job["function"].rsplit(".", 1)
            function = getattr(import_module(module_name), function_name)
            if "minutes" in job:
                scheduler.add_job(function, "interval", minutes=job["minutes"], id=job["function"])
            else:
                scheduler.add_job(function, "cron", hour=job["hour"], id=job["function"])
            self.stdout.write(f"scheduled {job['function']}")
        if not JOBS:
            self.stdout.write("No jobs registered yet (see common/jobs.py).")
            return
        scheduler.start()
