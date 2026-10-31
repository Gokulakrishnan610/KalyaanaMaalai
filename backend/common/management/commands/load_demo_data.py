from importlib import import_module

from django.core.management.base import BaseCommand
from django.db import transaction

from live.signals import silenced

# Run in this order: later files rely on earlier ones. Each file has a load() function.
DEMO_FILES = [
    "demo_data.people_and_enquiries",
    "demo_data.starter_wedding",
    "demo_data.weddings_and_tasks",
    "demo_data.vendors_and_quotations",
    "demo_data.payments",
    "demo_data.portal_and_agreements",
]


class Command(BaseCommand):
    help = "Fill the database with the demo data: staff, vendors, couples (with website logins), agreements and payments. Safe to run more than once."

    def handle(self, *args, **options):
        # silenced is outside the transaction, so the "after commit" emails are skipped too
        with silenced(), transaction.atomic():  # demo data should not flood the live feed, the bell or anyone's inbox
            self.load_all()

    def load_all(self):
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
