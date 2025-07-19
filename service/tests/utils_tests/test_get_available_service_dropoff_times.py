from django.test import TestCase
from django.utils import timezone
import datetime
from unittest.mock import patch
from service.utils.get_available_service_dropoff_times import (
    get_available_dropoff_times,
)
from service.models import ServiceSettings, ServiceBooking
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceSettingsFactory,
)


class GetAvailableDropoffTimesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixed_now_utc = datetime.datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc
        )

        cls.fixed_now_local_datetime = datetime.datetime(2025, 6, 15, 12, 0, 0)
        cls.fixed_local_date = datetime.date(2025, 6, 15)

        cls.patcher_now = patch(
            "django.utils.timezone.now", return_value=cls.fixed_now_utc
        )

        cls.patcher_localdate = patch(
            "django.utils.timezone.localdate", return_value=cls.fixed_local_date
        )

        cls.mock_now = cls.patcher_now.start()
        cls.mock_localdate = cls.patcher_localdate.start()

        timezone.activate("Europe/Copenhagen")

    @classmethod
    def tearDownClass(cls):
        cls.patcher_now.stop()
        cls.patcher_localdate.stop()
        timezone.deactivate()
        super().tearDownClass()

    def setUp(self):
        ServiceSettings.objects.all().delete()
        ServiceBooking.objects.all().delete()

        self.service_settings = ServiceSettingsFactory(
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            drop_off_spacing_mins=30,
            latest_same_day_dropoff_time=datetime.time(17, 0),
            enable_after_hours_dropoff=False,
        )

    def test_no_service_settings(self):
        ServiceSettings.objects.all().delete()
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, [])

    def test_basic_slot_generation_today(self):
        with patch(
            "django.utils.timezone.now",
            return_value=datetime.datetime(
                2025, 6, 15, 9, 30, 1, tzinfo=datetime.timezone.utc
            ),
        ):
            self.service_settings.drop_off_start_time = datetime.time(9, 0)
            self.service_settings.drop_off_end_time = datetime.time(17, 0)
            self.service_settings.drop_off_spacing_mins = 30
            self.service_settings.latest_same_day_dropoff_time = datetime.time(17, 0)
            self.service_settings.save()

            expected_times = [
                "12:00",
                "12:30",
                "13:00",
                "13:30",
                "14:00",
                "14:30",
                "15:00",
                "15:30",
                "16:00",
                "16:30",
                "17:00",
            ]
            available_times = get_available_dropoff_times(self.fixed_local_date)
            self.assertEqual(available_times, expected_times)

    def test_basic_slot_generation_future_date(self):
        future_date = self.fixed_local_date + datetime.timedelta(days=7)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(17, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.save()

        expected_times = [
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
        ]
        available_times = get_available_dropoff_times(future_date)
        self.assertEqual(available_times, expected_times)

    def test_slots_blocked_by_existing_bookings(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 30

        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0)
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(10, 0))

        expected_times = ["09:00", "11:00", "11:30", "12:00"]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_slots_blocked_by_multiple_bookings(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 30

        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0)
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(9, 30))
        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(11, 0))

        expected_times = ["12:00"]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_enable_after_hours_dropoff_true(self):
        self.service_settings.enable_after_hours_dropoff = True
        self.service_settings.drop_off_spacing_mins = 60

        self.service_settings.drop_off_start_time = datetime.time(0, 0)
        self.service_settings.drop_off_end_time = datetime.time(23, 59)
        self.service_settings.latest_same_day_dropoff_time = datetime.time(23, 59)
        self.service_settings.save()

        expected_times = [f"{h:02d}:00" for h in range(12, 24)]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

    def test_enable_after_hours_dropoff_true_with_booking(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.enable_after_hours_dropoff = True
        self.service_settings.drop_off_spacing_mins = 60

        self.service_settings.drop_off_start_time = datetime.time(0, 0)
        self.service_settings.drop_off_end_time = datetime.time(23, 59)
        self.service_settings.latest_same_day_dropoff_time = datetime.time(23, 59)
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(1, 0))

        expected_times = [f"{h:02d}:00" for h in range(24) if h not in [0, 1, 2]]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_drop_off_spacing_mins_60(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)

        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.save()

        expected_times = ["09:00", "10:00", "11:00", "12:00"]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_drop_off_spacing_mins_15(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 45)

        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 45)
        self.service_settings.drop_off_spacing_mins = 15
        self.service_settings.save()

        expected_times = ["09:00", "09:15", "09:30", "09:45"]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_selected_date_in_past_no_after_hours(self):
        past_date = self.fixed_local_date - datetime.timedelta(days=7)
        self.service_settings.enable_after_hours_dropoff = False
        self.service_settings.save()

        available_times = get_available_dropoff_times(past_date)
        self.assertEqual(available_times, [])

    def test_current_time_boundary(self):
        with patch(
            "django.utils.timezone.now",
            return_value=datetime.datetime(
                2025, 6, 15, 8, 15, 0, tzinfo=datetime.timezone.utc
            ),
        ):
            self.service_settings.drop_off_start_time = datetime.time(9, 0)
            self.service_settings.drop_off_end_time = datetime.time(12, 0)
            self.service_settings.drop_off_spacing_mins = 30

            self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0)
            self.service_settings.save()

            expected_times = ["10:30", "11:00", "11:30", "12:00"]
            available_times = get_available_dropoff_times(self.fixed_local_date)
            self.assertEqual(available_times, expected_times)

    def test_latest_same_day_dropoff_time_restriction(self):
        with patch(
            "django.utils.timezone.now",
            return_value=datetime.datetime(
                2025, 6, 15, 5, 0, 0, tzinfo=datetime.timezone.utc
            ),
        ):
            self.service_settings.drop_off_start_time = datetime.time(9, 0)
            self.service_settings.drop_off_end_time = datetime.time(17, 0)
            self.service_settings.drop_off_spacing_mins = 30
            self.service_settings.latest_same_day_dropoff_time = datetime.time(10, 0)
            self.service_settings.save()

            expected_times = ["09:00", "09:30", "10:00"]
            available_times = get_available_dropoff_times(self.fixed_local_date)
            self.assertEqual(available_times, expected_times)

    def test_full_day_blocked_by_booking(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 30)

        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 30)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(9, 0))

        expected_times = []
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_timezone_awareness(self):
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 30)

        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 30)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        available_times = get_available_dropoff_times(test_date)

        self.assertIsInstance(available_times, list)
        self.assertGreater(len(available_times), 0)
