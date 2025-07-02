from django.test import TestCase, Client
from django.urls import reverse
import datetime
from unittest.mock import patch


from service.models import BlockedServiceDate, ServiceBooking
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    BlockedServiceDateFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    ServiceTypeFactory,
    CustomerMotorcycleFactory,
)


from faker import Faker

fake = Faker()


class AjaxGetServiceDateAvailabilityTest(TestCase):

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

        self.client = Client()

        self.service_settings.booking_advance_notice = 1
        self.service_settings.max_visible_slots_per_day = 3
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        BlockedServiceDate.objects.all().delete()
        ServiceBooking.objects.all().delete()

    def test_ajax_success_response(self):

        expected_min_date = (
            self.fixed_local_date + datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")

        response = self.client.get(
            reverse("service:admin_api_service_date_availability")
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("min_date", data)
        self.assertIn("disabled_dates", data)
        self.assertIsInstance(data["disabled_dates"], list)
        self.assertEqual(data["min_date"], expected_min_date)

        self.assertEqual(len(data["disabled_dates"]), 0)

    def test_ajax_response_with_blocked_dates(self):

        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 20), end_date=datetime.date(2025, 6, 20)
        )

        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 25), end_date=datetime.date(2025, 6, 27)
        )

        response = self.client.get(
            reverse("service:admin_api_service_date_availability")
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        disabled_dates = data["disabled_dates"]

        self.assertIn({"from": "2025-06-20", "to": "2025-06-20"}, disabled_dates)
        self.assertIn({"from": "2025-06-25", "to": "2025-06-27"}, disabled_dates)

    def test_ajax_response_with_capacity_full(self):

        self.service_settings.max_visible_slots_per_day = 1
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        today = self.fixed_local_date

        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(9, 0, 0),
            booking_status="confirmed",
        )

        response = self.client.get(
            reverse("service:admin_api_service_date_availability")
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        disabled_dates = data["disabled_dates"]
        self.assertIn(str(today), disabled_dates)

    def test_ajax_response_with_non_booking_open_days(self):

        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        response = self.client.get(
            reverse("service:admin_api_service_date_availability")
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        disabled_dates = data["disabled_dates"]

        self.assertIn("2025-06-15", disabled_dates)

        self.assertNotIn("2025-06-16", disabled_dates)

        self.assertNotIn("2025-06-17", disabled_dates)

        self.assertIn("2025-06-18", disabled_dates)

    def test_ajax_error_handling(self):

        with patch(
            "service.ajax.ajax_get_available_service_dates.get_service_date_availability",
            side_effect=Exception("Simulated utility error"),
        ):
            response = self.client.get(
                reverse("service:admin_api_service_date_availability")
            )

            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn("error", data)
            self.assertEqual(
                data["error"], "Could not retrieve service date availability."
            )
