from django.apps import AppConfig


class LiveConfig(AppConfig):
    name = "live"

    def ready(self):
        from live import signals  # noqa: F401  (connects the signal handlers)
