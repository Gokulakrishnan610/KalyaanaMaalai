from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Customer(models.Model):
    """A couple's account on the customer website. Separate from staff users, so a customer can never reach staff screens."""

    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password_hash = models.CharField(max_length=255)
    # the CRM enquiry made when they signed up, and the client it becomes once the planner converts it
    enquiry = models.OneToOneField("enquiries.Enquiry", null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="portal_customer")
    client = models.ForeignKey("clients.Client", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="portal_customers")
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # lets Django REST Framework treat a Customer like a logged-in user
    is_authenticated = True
    is_anonymous = False

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def set_password(self, raw: str) -> None:
        self.password_hash = make_password(raw)

    def check_password(self, raw: str) -> bool:
        return check_password(raw, self.password_hash)
