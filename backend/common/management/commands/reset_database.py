from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Delete every table so you can start fresh. Development only."

    def handle(self, *args, **options):
        if settings.ENVIRONMENT != "dev":
            raise CommandError("This only runs when ENVIRONMENT=dev")
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")
        self.stdout.write("Database emptied. Now run: python manage.py migrate")
