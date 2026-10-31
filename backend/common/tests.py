from unittest import mock

from django.test import TestCase, override_settings

from common import jobs
from common.tasks import run_job
from config.celery import build_schedule


class CeleryTests(TestCase):
    def test_every_listed_job_gets_a_schedule_entry(self):
        schedule = build_schedule()
        self.assertEqual(set(schedule), {job["function"] for job in jobs.JOBS})
        late = schedule["weddings.jobs.mark_late_vendors"]
        self.assertEqual((late["task"], late["schedule"]), ("common.run_job", 60.0))

    def test_run_job_calls_the_listed_function(self):
        with mock.patch("weddings.jobs.mark_late_vendors", return_value=3) as job:
            self.assertEqual(run_job("weddings.jobs.mark_late_vendors"), 3)
        job.assert_called_once()

    def test_jobs_can_be_added_with_a_minutes_or_hour_rule(self):
        extra = [{"function": "a.b.c", "minutes": 5}, {"function": "d.e.f", "hour": 7}]
        with mock.patch.object(jobs, "JOBS", extra):
            schedule = build_schedule()
        self.assertEqual(schedule["a.b.c"]["schedule"], 300.0)
        self.assertEqual(schedule["d.e.f"]["schedule"].hour, {7})


@override_settings(MOCK_EXTERNALS=False, TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="1")
class TelegramQueueTests(TestCase):
    def test_telegram_goes_through_the_background_queue(self):
        from notifications.services import notify

        with mock.patch("notifications.tasks.send_telegram_now") as send:  # eager in tests: runs on the spot
            notify("Caterer is late", channel="telegram")
        send.assert_called_once_with("Caterer is late", "info")

    def test_if_the_queue_is_down_it_is_sent_directly(self):
        from notifications.services import notify

        with mock.patch("notifications.tasks.send_telegram.apply_async", side_effect=ConnectionError), \
                mock.patch("notifications.services.send_telegram_now") as send:
            notify("Caterer is late", channel="telegram")
        send.assert_called_once()
