from django.db import models


class Client(models.Model):
    """The couple who hire Shaandaar Events."""

    couple_name = models.CharField(max_length=200)
    bride_name = models.CharField(max_length=120, blank=True)
    groom_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.couple_name
