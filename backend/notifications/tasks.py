from celery import shared_task

from notifications.services import send_telegram_now


@shared_task(name="notifications.send_telegram", ignore_result=True)
def send_telegram(message: str, severity: str = "info"):
    send_telegram_now(message, severity)
