from django.apps import AppConfig


class MailerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mailer"

    def ready(self):
        from mailer import signals  # noqa: F401
