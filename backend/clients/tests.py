from datetime import date

from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from payments.models import Invoice, Payment
from weddings.models import Wedding


class ClientTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.couple = Client.objects.create(couple_name="Aarav & Meera", phone="9876543210", city="Jaipur")

    def test_profile_shows_what_the_couple_still_owes(self):
        wedding = Wedding.objects.create(title="Aarav & Meera wedding", client=self.couple,
                                         start_date=date(2027, 2, 10), end_date=date(2027, 2, 12), city="Jaipur",
                                         guest_count=450, contracted_guests=450)
        invoice = Invoice.objects.create(wedding=wedding, client=self.couple, kind="DEPOSIT",
                                         amount_paise=500000_00)
        Payment.objects.create(wedding=wedding, invoice=invoice, direction="IN", amount_paise=200000_00,
                               method="UPI")
        self.client.force_authenticate(self.planner)
        res = self.client.get(f"/api/clients/{self.couple.id}/")
        self.assertEqual(res.data["invoiced_paise"], 500000_00)
        self.assertEqual(res.data["paid_paise"], 200000_00)
        self.assertEqual(res.data["outstanding_paise"], 300000_00)
        self.assertEqual(len(res.data["weddings"]), 1)

    def test_search_and_phone_validation(self):
        self.client.force_authenticate(self.planner)
        self.assertEqual(self.client.get("/api/clients/?q=jaipur").data["count"], 1)
        res = self.client.post("/api/clients/", {"couple_name": "X & Y", "phone": "abc"})
        self.assertEqual(res.status_code, 400)
