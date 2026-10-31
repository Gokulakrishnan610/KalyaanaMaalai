from importlib import import_module

from django.core.management.base import BaseCommand
from django.db import transaction

# Run in this order: later files rely on earlier ones. Each file has a load() function.
DEMO_FILES = [
    "demo_data.people_and_enquiries",
    "demo_data.weddings_and_tasks",
    "demo_data.vendors_and_quotations",
    "demo_data.payments",
]


class Command(BaseCommand):
    help = "Fill the database with the Aarav & Meera demo wedding. Safe to run more than once."

    @transaction.atomic
    def handle(self, *args, **options):
        for name in DEMO_FILES:
            try:
                module = import_module(name)
            except ModuleNotFoundError as error:
                if error.name != name:
                    raise
                self.stdout.write(f"skipped {name} (not written yet)")
                continue
            module.load()
            self.stdout.write(f"loaded {name}")
