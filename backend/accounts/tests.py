from rest_framework.test import APITestCase

from accounts.models import Role, User


class LoginAndUsersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("founder@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("planner@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("staff@t.com", "Staff", "Password123", role=Role.STAFF)

    def login(self, email):
        res = self.client.post("/api/auth/login/", {"email": email, "password": "Password123"})
        self.assertEqual(res.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_login_returns_token_and_user(self):
        res = self.client.post("/api/auth/login/", {"email": "founder@t.com", "password": "Password123"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["user"]["role"], "FOUNDER")
        self.assertIn("access", res.data)

    def test_wrong_password_is_rejected(self):
        res = self.client.post("/api/auth/login/", {"email": "founder@t.com", "password": "wrong"})
        self.assertEqual(res.status_code, 400)

    def test_me_needs_a_token(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.login("staff@t.com")
        self.assertEqual(self.client.get("/api/auth/me/").data["email"], "staff@t.com")

    def test_staff_cannot_see_or_create_users(self):
        self.login("staff@t.com")
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        body = {"name": "X", "email": "x@t.com", "password": "Password123"}
        self.assertEqual(self.client.post("/api/users/", body).status_code, 403)

    def test_planner_can_list_but_not_create(self):
        self.login("planner@t.com")
        self.assertEqual(self.client.get("/api/users/").status_code, 200)
        body = {"name": "X", "email": "x@t.com", "password": "Password123"}
        self.assertEqual(self.client.post("/api/users/", body).status_code, 403)

    def test_founder_creates_user_and_duplicate_email_is_refused(self):
        self.login("founder@t.com")
        body = {"name": "New", "email": "new@t.com", "password": "Password123", "role": "STAFF"}
        self.assertEqual(self.client.post("/api/users/", body).status_code, 201)
        self.assertEqual(self.client.post("/api/users/", body).status_code, 400)
