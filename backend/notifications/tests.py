from unittest import mock

from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Role, User
from notifications import services
from notifications.models import Notification


class NotifyTests(APITestCase):
    def test_always_saves_a_row_even_without_telegram(self):
        note = services.notify("Hello", channel="both", severity="warning")
        self.assertEqual((note.message, note.severity, note.channel), ("Hello", "warning", "both"))

    @override_settings(MOCK_EXTERNALS=True, TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_mock_mode_never_calls_telegram(self):
        with mock.patch.object(services.httpx, "post") as post:
            services.notify("Hi")
        post.assert_not_called()

    @override_settings(MOCK_EXTERNALS=False, TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_live_mode_posts_to_telegram_with_a_5_second_timeout(self):
        with mock.patch.object(services.httpx, "post") as post:
            services.notify("Caterer is late")
        self.assertEqual(post.call_args.args[0], "https://api.telegram.org/bot123:abc/sendMessage")
        self.assertEqual((post.call_args.kwargs["timeout"], post.call_args.kwargs["json"]),
                         (5, {"chat_id": "42", "text": "Caterer is late"}))

    @override_settings(MOCK_EXTERNALS=False, TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_a_telegram_failure_is_swallowed_and_the_secret_is_not_logged(self):
        with mock.patch.object(services.httpx, "post", side_effect=RuntimeError("boom 123:abc")):
            with self.assertLogs("notifications.services", level="WARNING") as logs:
                note = services.notify("x")
        self.assertIsNotNone(note)
        self.assertNotIn("123:abc", "".join(logs.output))

    @override_settings(MOCK_EXTERNALS=False, TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_inapp_channel_never_calls_telegram(self):
        with mock.patch.object(services.httpx, "post") as post:
            services.notify("x", channel="inapp")
        post.assert_not_called()

    def test_the_same_dedupe_key_is_saved_only_once(self):
        self.assertIsNotNone(services.notify("a", dedupe_key="k1"))
        self.assertIsNone(services.notify("a", dedupe_key="k1"))
        self.assertEqual(Notification.objects.count(), 1)


class NotificationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user("me@t.com", "Me", "Password123", role=Role.PLANNER)
        cls.other = User.objects.create_user("o@t.com", "Other", "Password123", role=Role.PLANNER)

    def setUp(self):
        self.client.force_authenticate(self.me)

    def test_shows_my_alerts_and_broadcasts_but_not_other_peoples(self):
        services.notify("for everyone")
        services.notify("for me", user_id=self.me.pk)
        services.notify("for them", user_id=self.other.pk)
        res = self.client.get("/api/notifications/").data
        self.assertEqual(res["unread_count"], 2)
        self.assertEqual({n["message"] for n in res["results"]}, {"for everyone", "for me"})

    def test_newest_first_and_marking_read(self):
        first = services.notify("one")
        services.notify("two")
        res = self.client.get("/api/notifications/").data
        self.assertEqual([n["message"] for n in res["results"]], ["two", "one"])
        marked = self.client.patch(f"/api/notifications/{first.pk}/read/")
        self.assertTrue(marked.data["is_read"])
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 1)
        self.assertEqual(len(self.client.get("/api/notifications/?unread=1").data["results"]), 1)

    def test_read_all(self):
        for text in "abc":
            services.notify(text)
        self.assertEqual(self.client.post("/api/notifications/read-all/").data["marked_read"], 3)
        self.assertEqual(self.client.get("/api/notifications/").data["unread_count"], 0)

    def test_cannot_mark_someone_elses_alert(self):
        theirs = services.notify("secret", user_id=self.other.pk)
        self.assertEqual(self.client.patch(f"/api/notifications/{theirs.pk}/read/").status_code, 404)

    def test_login_is_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 401)
