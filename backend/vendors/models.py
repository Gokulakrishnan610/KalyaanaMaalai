from django.db import models


class VendorCategory(models.Model):
    """Caterer, Decorator, DJ, Photographer ..."""

    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "vendor categories"

    def __str__(self):
        return self.name


class Vendor(models.Model):
    """A supplier we hire for weddings."""

    name = models.CharField(max_length=200, db_index=True)
    category = models.ForeignKey(VendorCategory, on_delete=models.PROTECT, related_name="vendors")
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
