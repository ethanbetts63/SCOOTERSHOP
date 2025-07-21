from django.test import TestCase
import datetime
import json
from unittest.mock import patch


from service.utils.get_service_date_availibility import get_service_date_availability


from service.models import ServiceSettings, BlockedServiceDate, ServiceBooking


from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceProfileFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
    CustomerMotorcycleFactory,
    BlockedServiceDateFactory,
)

from faker import Faker

fake = Faker()


class GetServiceDateAvailabilityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixed_now = datetime.datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        cls.fixed_local_date = datetime.date(2025, 6, 15)

        cls.patcher_now = patch("django.utils.timezone.now", return_value=cls.fixed_now)
        cls.patcher_localtime = patch(
            "django.utils.timezone.localtime", return_value=cls.fixed_now
        )

        cls.mock_now = cls.patcher_now.start()
        cls.mock_localtime = cls.patcher_localtime.start()

        cls.service_settings = ServiceSettingsFactory(
            booking_advance_notice=1,
            max_visible_slots_per_day=3,
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        )

        cls.service_profile = ServiceProfileFactory()
        cls.service_type = ServiceTypeFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(
            service_profile=cls.service_profile
        )

    @classmethod
    def tearDownClass(cls):
        cls.patcher_now.stop()
        cls.patcher_localtime.stop()
        super().tearDownClass()

    def setUp(self):
        self.service_settings.booking_advance_notice = 1
        self.service_settings.max_visible_slots_per_day = 3
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        BlockedServiceDate.objects.all().delete()
        ServiceBooking.objects.all().delete()

    def test_min_date_with_advance_notice(self):
        self.service_settings.booking_advance_notice = 1
        self.service_settings.save()
        min_date, _ = get_service_date_availability()
        expected_min_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.assertEqual(min_date, expected_min_date)

        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()
        min_date, _ = get_service_date_availability()
        expected_min_date = self.fixed_local_date
        self.assertEqual(min_date, expected_min_date)

        self.service_settings.booking_advance_notice = 7
        self.service_settings.save()
        min_date, _ = get_service_date_availability()
        expected_min_date = self.fixed_local_date + datetime.timedelta(days=7)
        self.assertEqual(min_date, expected_min_date)

    def test_blocked_service_dates(self):
        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 20), end_date=datetime.date(2025, 6, 20)
        )

        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 25), end_date=datetime.date(2025, 6, 27)
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn({"from": "2025-06-20", "to": "2025-06-20"}, disabled_dates)

        self.assertIn({"from": "2025-06-25", "to": "2025-06-27"}, disabled_dates)

    def test_non_booking_open_days(self):
        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn("2025-06-15", disabled_dates)

        self.assertNotIn("2025-06-16", disabled_dates)

        self.assertNotIn("2025-06-17", disabled_dates)

        self.assertIn("2025-06-18", disabled_dates)

        self.assertIn("2025-06-19", disabled_dates)

        self.assertIn("2025-06-20", disabled_dates)

        self.assertIn("2025-06-21", disabled_dates)

        self.assertIn("2025-06-22", disabled_dates)

    def test_max_visible_slots_capacity(self):
        self.service_settings.max_visible_slots_per_day = 1
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        today = self.fixed_local_date
        tomorrow = today + datetime.timedelta(days=1)

        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(9, 0, 0),
            booking_status="confirmed",
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn(str(today), disabled_dates)
        self.assertNotIn(str(tomorrow), disabled_dates)

        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=tomorrow,
            service_date=tomorrow,
            dropoff_time=datetime.time(9, 30, 0),
            booking_status="in_progress",
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn(str(today), disabled_dates)
        self.assertIn(str(tomorrow), disabled_dates)

    def test_combined_rules(self):
        self.service_settings.booking_advance_notice = 0
        self.service_settings.max_visible_slots_per_day = 1
        self.service_settings.booking_open_days = "Mon"
        self.service_settings.save()

        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 17), end_date=datetime.date(2025, 6, 17)
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn("2025-06-15", disabled_dates)

        self.assertNotIn("2025-06-16", disabled_dates)

        self.assertIn({"from": "2025-06-17", "to": "2025-06-17"}, disabled_dates)

        self.assertIn("2025-06-17", disabled_dates)

        self.assertNotIn("2025-06-23", disabled_dates)

    def test_no_service_settings(self):
        ServiceSettings.objects.all().delete()

        BlockedServiceDateFactory(
            start_date=self.fixed_local_date + datetime.timedelta(days=5),
            end_date=self.fixed_local_date + datetime.timedelta(days=5),
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertEqual(min_date, self.fixed_local_date)

        expected_blocked = {
            "from": str(self.fixed_local_date + datetime.timedelta(days=5)),
            "to": str(self.fixed_local_date + datetime.timedelta(days=5)),
        }
        self.assertEqual(len(disabled_dates), 1)
        self.assertIn(expected_blocked, disabled_dates)

    def test_empty_booking_open_days(self):
        self.service_settings.booking_open_days = "INVALID"
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        for i in range(366):
            expected_date = self.fixed_local_date + datetime.timedelta(days=i)
            self.assertIn(str(expected_date), disabled_dates)

        self.service_settings.booking_open_days = " "
        self.service_settings.save()

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)
        for i in range(366):
            expected_date = self.fixed_local_date + datetime.timedelta(days=i)
            self.assertIn(str(expected_date), disabled_dates)

    def test_no_max_visible_slots_per_day_set(self):
        self.service_settings.max_visible_slots_per_day = 99999
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        today = self.fixed_local_date

        for _ in range(10):
            ServiceBookingFactory(
                service_profile=self.service_profile,
                service_type=self.service_type,
                customer_motorcycle=self.customer_motorcycle,
                dropoff_date=today,
                service_date=today,
                dropoff_time=datetime.time(9, 0, 0),
                booking_status="confirmed",
            )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertNotIn(str(today), disabled_dates)

    def test_booking_status_filter(self):
        self.service_settings.daily_service_slots = 1
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        today = self.fixed_local_date

        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(10, 0, 0),
            booking_status="pending",
        )

        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(11, 0, 0),
            booking_status="cancelled",
        )

        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(12, 0, 0),
            booking_status="DECLINED_REFUNDED",
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn(str(today), disabled_dates)
