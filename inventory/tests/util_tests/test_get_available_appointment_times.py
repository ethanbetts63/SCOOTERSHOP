from django.test import TestCase
from datetime import datetime, time, timedelta
from django.utils import timezone

from inventory.utils.get_available_appointment_times import (
    get_available_appointment_times,
)
from ..test_helpers.model_factories import InventorySettingsFactory, SalesBookingFactory


class GetAvailableAppointmentTimesUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):

        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=1,
        )
        cls.today = timezone.localdate(timezone.now())

    def test_no_inventory_settings(self):
        selected_date = self.today
        available_times = get_available_appointment_times(selected_date, None)
        self.assertEqual(available_times, [])

    def test_basic_time_slot_generation(self):

        future_date = self.today + timedelta(days=7)
        available_times = get_available_appointment_times(
            future_date, self.inventory_settings
        )

        expected_times = [
            "09:00",
            "09:30",
            "10:00",
            "10:30",
            "11:00",
            "11:30",
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
        self.assertEqual(available_times, expected_times)

    def test_excludes_times_too_soon_for_today(self):

        settings_today = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=2,
            pk=200,
        )

        now = timezone.now()
        earliest_valid_datetime = now + timedelta(
            hours=settings_today.min_advance_booking_hours
        )

        available_times = get_available_appointment_times(self.today, settings_today)

        for time_str in available_times:
            test_datetime = timezone.make_aware(
                datetime.combine(
                    self.today, datetime.strptime(time_str, "%H:%M").time()
                ),
                timezone=timezone.get_current_timezone(),
            )
            self.assertGreater(test_datetime, earliest_valid_datetime)

    def test_excludes_single_booked_slot(self):

        selected_date = self.today + timedelta(days=1)
        booked_time = time(10, 0)
        SalesBookingFactory(
            appointment_date=selected_date,
            appointment_time=booked_time,
            booking_status="confirmed",
        )

        available_times = get_available_appointment_times(
            selected_date, self.inventory_settings
        )

        self.assertNotIn("10:00", available_times)

        self.assertNotIn("09:30", available_times)
        self.assertNotIn("10:30", available_times)

        self.assertIn("09:00", available_times)
        self.assertIn("11:00", available_times)

    def test_excludes_multiple_booked_slots(self):
        selected_date = self.today + timedelta(days=2)
        SalesBookingFactory(
            appointment_date=selected_date,
            appointment_time=time(9, 30),
            booking_status="confirmed",
        )
        SalesBookingFactory(
            appointment_date=selected_date,
            appointment_time=time(11, 0),
            booking_status="reserved",
        )
        SalesBookingFactory(
            appointment_date=selected_date,
            appointment_time=time(15, 0),
            booking_status="confirmed",
        )

        available_times = get_available_appointment_times(
            selected_date, self.inventory_settings
        )

        self.assertNotIn("09:00", available_times)
        self.assertNotIn("09:30", available_times)
        self.assertNotIn("10:00", available_times)

        self.assertNotIn("10:30", available_times)
        self.assertNotIn("11:00", available_times)
        self.assertNotIn("11:30", available_times)

        self.assertNotIn("14:30", available_times)
        self.assertNotIn("15:00", available_times)
        self.assertNotIn("15:30", available_times)

        self.assertIn("12:00", available_times)
        self.assertIn("13:00", available_times)
        self.assertIn("16:00", available_times)

    def test_booked_slot_with_different_status_does_not_block(self):
        selected_date = self.today + timedelta(days=3)

        SalesBookingFactory(
            appointment_date=selected_date,
            appointment_time=time(10, 0),
            booking_status="cancelled",
        )

        available_times = get_available_appointment_times(
            selected_date, self.inventory_settings
        )

        self.assertIn("10:00", available_times)
        self.assertIn("09:30", available_times)
        self.assertIn("10:30", available_times)

    def test_bookings_on_different_date_do_not_block(self):
        selected_date = self.today + timedelta(days=4)

        SalesBookingFactory(
            appointment_date=selected_date + timedelta(days=1),
            appointment_time=time(10, 0),
            booking_status="confirmed",
        )

        available_times = get_available_appointment_times(
            selected_date, self.inventory_settings
        )

        self.assertIn("10:00", available_times)
