from django.db import migrations

CATEGORIES = ["Caterer", "Decorator", "DJ & Sound", "Photographer", "Videographer", "Makeup Artist",
              "Mehendi Artist", "Venue", "Transport", "Florist", "Invitation Printer"]


def add_categories(apps, schema_editor):
    VendorCategory = apps.get_model("vendors", "VendorCategory")
    for name in CATEGORIES:
        VendorCategory.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("vendors", "0001_initial")]
    operations = [migrations.RunPython(add_categories, migrations.RunPython.noop)]
