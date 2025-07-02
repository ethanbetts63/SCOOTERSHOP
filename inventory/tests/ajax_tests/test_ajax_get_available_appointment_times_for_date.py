import datetime
from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import InventorySettings
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    SalesBookingFactory,
    MotorcycleFactory,
    SalesProfileFactory,
)


class GetAvailableAppointmentTimesForDateAjaxTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.client = Client()

        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=0,
        )

        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()

        cls.ajax_url = reverse("inventory:ajax_get_appointment_times")

    def test_missing_date_parameter(self):

        response = self.client.get(self.ajax_url)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content, {"error": "Date parameter (selected_date) is missing."}
        )

    def test_invalid_date_format(self):

        response = self.client.get(f"{self.ajax_url}?selected_date=2025/06/24")
        self.assertEqual(response.status_code, 400)

        self.assertJSONEqual(
            response.content, {"error": "Invalid date format. Use YYYY-MM-DD."}
        )

    def test_no_inventory_settings(self):

        InventorySettings.objects.all().delete()
        response = self.client.get(f"{self.ajax_url}?selected_date=2025-06-24")
        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content, {"error": "Inventory settings not found."}
        )

        self.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=0,
        )

    def test_get_available_times_no_bookings(self):

        test_date = datetime.date.today() + datetime.timedelta(days=1)
        response = self.client.get(
            f"{self.ajax_url}?selected_date={test_date.strftime('%Y-%m-%d')}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("available_times", data)

        expected_times = []
        current_time = datetime.datetime.combine(
            test_date, self.inventory_settings.sales_appointment_start_time
        )
        end_time_limit = datetime.datetime.combine(
            test_date, self.inventory_settings.sales_appointment_end_time
        )

        while current_time <= end_time_limit:
            expected_times.append(
                {
                    "value": current_time.strftime("%H:%M"),
                    "display": current_time.strftime("%I:%M %p"),
                }
            )
            current_time += datetime.timedelta(
                minutes=self.inventory_settings.sales_appointment_spacing_mins
            )

        self.assertEqual(len(data["available_times"]), len(expected_times))
        self.assertEqual(data["available_times"], expected_times)

    def test_get_available_times_with_existing_bookings(self):

        test_date = datetime.date.today() + datetime.timedelta(days=2)

        SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            appointment_date=test_date,
            appointment_time=datetime.time(10, 0),
            booking_status="confirmed",
        )

        SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            appointment_date=test_date,
            appointment_time=datetime.time(14, 30),
            booking_status="reserved",
        )

        response = self.client.get(
            f"{self.ajax_url}?selected_date={test_date.strftime('%Y-%m-%d')}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("available_times", data)

        all_potential_slots = []
        current_time_obj = self.inventory_settings.sales_appointment_start_time
        end_time_obj = self.inventory_settings.sales_appointment_end_time
        while current_time_obj <= end_time_obj:
            all_potential_slots.append(current_time_obj)
            dt_current_slot = datetime.datetime.combine(test_date, current_time_obj)
            dt_current_slot += datetime.timedelta(
                minutes=self.inventory_settings.sales_appointment_spacing_mins
            )
            current_time_obj = dt_current_slot.time()

        blocked_raw_times = [
            datetime.time(9, 30),
            datetime.time(10, 0),
            datetime.time(10, 30),
            datetime.time(14, 0),
            datetime.time(14, 30),
            datetime.time(15, 0),
        ]

        expected_available_times = []
        for slot_time_obj in all_potential_slots:
            if slot_time_obj not in blocked_raw_times:
                expected_available_times.append(
                    {
                        "value": slot_time_obj.strftime("%H:%M"),
                        "display": slot_time_obj.strftime("%I:%M %p"),
                    }
                )

        self.assertEqual(len(data["available_times"]), len(expected_available_times))
        self.assertEqual(data["available_times"], expected_available_times)

    def test_get_available_times_min_advance_booking_hours(self):

        self.inventory_settings.min_advance_booking_hours = 48
        self.inventory_settings.save()

        today = datetime.date.today()
        response = self.client.get(
            f"{self.ajax_url}?selected_date={today.strftime('%Y-%m-%d')}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["available_times"], [])

        future_date = today + datetime.timedelta(days=3)
        response = self.client.get(
            f"{self.ajax_url}?selected_date={future_date.strftime('%Y-%m-%d')}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["available_times"]), 0)

        self.inventory_settings.min_advance_booking_hours = 0
        self.inventory_settings.save()
