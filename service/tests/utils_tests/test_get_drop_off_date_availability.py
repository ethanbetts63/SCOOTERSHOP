from django.test import TestCase
from django.utils import timezone
import datetime
from unittest.mock import patch


from service.utils.get_drop_off_date_availability import get_drop_off_date_availability


from service.models import ServiceSettings, BlockedServiceDate
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    TempServiceBookingFactory,
    BlockedServiceDateFactory,
)


class GetDropOffDateAvailabilityTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.fixed_now_utc = datetime.datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc
        )

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
        BlockedServiceDate.objects.all().delete()

        self.service_settings = ServiceSettingsFactory(
            max_advance_dropoff_days=7,
            enable_after_hours_dropoff=False,
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        )

        self.temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_local_date + datetime.timedelta(days=3)
        )

    def test_basic_availability_all_days_open(self):

        self.service_settings.max_advance_dropoff_days = 7
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.enable_after_hours_dropoff = False
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        expected_dates = ["2025-06-15", "2025-06-16", "2025-06-17", "2025-06-18"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_max_advance_dropoff_days_restriction(self):

        self.service_settings.max_advance_dropoff_days = 3
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=5
        )
        self.temp_booking.save()

        expected_dates = ["2025-06-17", "2025-06-18", "2025-06-19", "2025-06-20"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_dropoff_date_cannot_be_after_service_date(self):

        self.service_settings.max_advance_dropoff_days = 7
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=1
        )
        self.temp_booking.save()

        expected_dates = ["2025-06-15", "2025-06-16"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_blocked_service_date_single_day(self):

        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        BlockedServiceDateFactory(
            start_date=self.fixed_local_date + datetime.timedelta(days=1),
            end_date=self.fixed_local_date + datetime.timedelta(days=1),
        )

        expected_dates = ["2025-06-15", "2025-06-17", "2025-06-18"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_blocked_service_date_range(self):

        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=7
        )
        self.temp_booking.save()

        BlockedServiceDateFactory(
            start_date=self.fixed_local_date + datetime.timedelta(days=2),
            end_date=self.fixed_local_date + datetime.timedelta(days=4),
        )

        expected_dates = [
            "2025-06-15",
            "2025-06-16",
            "2025-06-20",
            "2025-06-21",
            "2025-06-22",
        ]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_enable_after_hours_dropoff_true_ignores_open_days(self):

        self.service_settings.enable_after_hours_dropoff = True
        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        expected_dates = ["2025-06-15", "2025-06-16", "2025-06-17", "2025-06-18"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_enable_after_hours_dropoff_false_respects_open_days(self):

        self.service_settings.enable_after_hours_dropoff = False
        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        expected_dates = ["2025-06-16", "2025-06-17"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_service_date_in_past(self):

        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date - datetime.timedelta(
            days=2
        )
        self.temp_booking.save()

        expected_dates = []
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_max_advance_days_is_zero(self):

        self.service_settings.max_advance_dropoff_days = 0
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        expected_dates = ["2025-06-18"]
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_empty_booking_open_days_no_after_hours(self):

        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.enable_after_hours_dropoff = False
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        dummy_settings = ServiceSettings(
            max_advance_dropoff_days=self.service_settings.max_advance_dropoff_days,
            enable_after_hours_dropoff=False,
            booking_open_days="",
        )

        expected_dates = []
        available_dates = get_drop_off_date_availability(
            self.temp_booking, dummy_settings
        )
        self.assertEqual(available_dates, expected_dates)

    def test_all_dates_blocked(self):

        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(
            days=3
        )
        self.temp_booking.save()

        BlockedServiceDateFactory(
            start_date=self.fixed_local_date,
            end_date=self.fixed_local_date + datetime.timedelta(days=3),
        )

        expected_dates = []
        available_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        self.assertEqual(available_dates, expected_dates)
