from django.test import TestCase
from inventory.forms import BookingAppointmentForm
from datetime import date, time, timedelta
from unittest.mock import Mock


class BookingAppointmentFormTest(TestCase):
    def setUp(self):
        self.mock_inventory_settings = Mock(
            min_advance_booking_hours=24, max_advance_booking_days=90
        )

    def test_valid_form_data(self):
        form = BookingAppointmentForm(
            data={
                "appointment_date": date.today() + timedelta(days=2),
                "appointment_time": time(10, 0),
                "customer_notes": "Some notes",
                "terms_accepted": True,
            },
            inventory_settings=self.mock_inventory_settings,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_appointment_date(self):
        form = BookingAppointmentForm(
            data={
                "appointment_time": time(10, 0),
                "terms_accepted": True,
            },
            inventory_settings=self.mock_inventory_settings,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("appointment_date", form.errors)
        self.assertIn("This field is required.", form.errors["appointment_date"])

    def test_missing_appointment_time(self):
        form = BookingAppointmentForm(
            data={
                "appointment_date": date.today() + timedelta(days=2),
                "terms_accepted": True,
            },
            inventory_settings=self.mock_inventory_settings,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("appointment_time", form.errors)
        self.assertIn("This field is required.", form.errors["appointment_time"])

    def test_terms_not_accepted(self):
        form = BookingAppointmentForm(
            data={
                "appointment_date": date.today() + timedelta(days=2),
                "appointment_time": time(10, 0),
                "terms_accepted": False,
            },
            inventory_settings=self.mock_inventory_settings,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("terms_accepted", form.errors)
        self.assertIn(
            "You must accept the terms and conditions.", form.errors["terms_accepted"]
        )

    def test_appointment_date_min_max_attributes(self):
        form = BookingAppointmentForm(inventory_settings=self.mock_inventory_settings)
        min_date = date.today() + timedelta(
            hours=self.mock_inventory_settings.min_advance_booking_hours
        )
        max_date = date.today() + timedelta(
            days=self.mock_inventory_settings.max_advance_booking_days
        )
        self.assertEqual(
            form.fields["appointment_date"].widget.attrs["min"],
            min_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            form.fields["appointment_date"].widget.attrs["max"],
            max_date.strftime("%Y-%m-%d"),
        )

    def test_form_fields_required_by_init(self):
        form = BookingAppointmentForm(inventory_settings=self.mock_inventory_settings)
        self.assertTrue(form.fields["appointment_date"].required)
        self.assertTrue(form.fields["appointment_time"].required)
        self.assertFalse(form.fields["customer_notes"].required)
        self.assertTrue(form.fields["terms_accepted"].required)
