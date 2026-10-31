from celery import shared_task

from mailer.services import deliver_now


@shared_task(name="mailer.deliver", ignore_result=True)
def deliver(log_id: int):
    deliver_now(log_id)
