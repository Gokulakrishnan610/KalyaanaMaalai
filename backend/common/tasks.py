from importlib import import_module

from celery import shared_task
from celery.signals import worker_ready


@shared_task(name="common.run_job")
def run_job(path: str):
    """Run one of the functions listed in common/jobs.py, e.g. "weddings.jobs.mark_late_vendors"."""
    module_name, function_name = path.rsplit(".", 1)
    return getattr(import_module(module_name), function_name)()


@worker_ready.connect
def run_start_jobs(**kwargs):
    """Jobs marked "run_at_start" also run once when the worker starts, so a fresh setup shows alerts at once."""
    from common.jobs import JOBS

    for job in JOBS:
        if job.get("run_at_start"):
            run_job.delay(job["function"])
