from django.db import models
from django.db.models.functions import Lower


class Client(models.Model):
    """The couple who hire Shaandaar Events."""

    couple_name = models.CharField(max_length=200)
    # the person we deal with, and their spouse. A client is recognised by client_name + email.
    client_name = models.CharField(max_length=200, blank=True)
    spouse_name = models.CharField(max_length=120, blank=True)
    spouse_email = models.EmailField(blank=True)
    bride_name = models.CharField(max_length=120, blank=True)
    groom_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # the same client name + email (ignoring capitals) can only exist once
            models.UniqueConstraint(
                Lower("client_name"), Lower("email"),
                condition=~models.Q(client_name="") & ~models.Q(email=""),
                name="one_client_per_name_and_email",
            ),
        ]

    def __str__(self):
        return self.couple_name
