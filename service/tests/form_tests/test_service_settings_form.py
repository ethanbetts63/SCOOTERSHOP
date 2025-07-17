from django.test import TestCase
from decimal import Decimal
from datetime import time

from service.forms import ServiceBookingSettingsForm


from service.tests.test_helpers.model_factories import ServiceSettingsFactory


class ServiceBookingSettingsFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service_settings = ServiceSettingsFactory()

        cls.valid_data = {
            "booking_advance_notice": 1,
            "max_visible_slots_per_day": 6,
            "booking_open_days": "Mon,Tue,Wed,Thu,Fri",
            "drop_off_start_time": time(9, 0),
            "drop_off_end_time": time(17, 0),
            "drop_off_spacing_mins": 30,
            "max_advance_dropoff_days": 7,
            "latest_same_day_dropoff_time": time(12, 0),
            "enable_after_hours_dropoff": False,
            "after_hours_dropoff_disclaimer": "Motorcycle drop-off outside of opening hours is at your own risk.",
            "deposit_calc_method": "FLAT_FEE",
            "deposit_flat_fee_amount": Decimal("25.00"),
            "deposit_percentage": Decimal("0.00"),
            "enable_online_full_payment": True,
            "enable_online_deposit": True,
            "enable_instore_full_payment": True,
            "currency_code": "AUD",
            "currency_symbol": "$",
        }

    def test_form_valid_data(self):
        form = ServiceBookingSettingsForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        self.assertIsInstance(form.cleaned_data["deposit_flat_fee_amount"], Decimal)
        self.assertIsInstance(form.cleaned_data["deposit_percentage"], Decimal)

        self.assertIsInstance(form.cleaned_data["drop_off_start_time"], time)
        self.assertIsInstance(form.cleaned_data["drop_off_end_time"], time)
        self.assertIsInstance(form.cleaned_data["latest_same_day_dropoff_time"], time)

    def test_form_initialization_with_instance(self):
        self.service_settings.booking_advance_notice = 5
        self.service_settings.deposit_flat_fee_amount = Decimal("100.00")
        self.service_settings.drop_off_start_time = time(8, 0)
        self.service_settings.drop_off_end_time = time(18, 0)

        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.max_advance_dropoff_days = 10
        self.service_settings.latest_same_day_dropoff_time = time(13, 0)
        self.service_settings.enable_after_hours_dropoff = True
        self.service_settings.after_hours_dropoff_disclaimer = "Test disclaimer."

        self.service_settings.save()

        form = ServiceBookingSettingsForm(instance=self.service_settings)
        self.assertEqual(form.initial["booking_advance_notice"], 5)
        self.assertEqual(form.initial["deposit_flat_fee_amount"], Decimal("100.00"))
        self.assertEqual(form.initial["drop_off_start_time"], time(8, 0))
        self.assertEqual(form.initial["drop_off_end_time"], time(18, 0))

        self.assertEqual(form.initial["drop_off_spacing_mins"], 60)
        self.assertEqual(form.initial["max_advance_dropoff_days"], 10)
        self.assertEqual(form.initial["latest_same_day_dropoff_time"], time(13, 0))
        self.assertEqual(form.initial["enable_after_hours_dropoff"], True)
        self.assertEqual(
            form.initial["after_hours_dropoff_disclaimer"], "Test disclaimer."
        )

    def test_form_save_updates_instance(self):
        data = self.valid_data.copy()
        data["booking_advance_notice"] = 10
        data["deposit_flat_fee_amount"] = Decimal("75.00")
        data["drop_off_start_time"] = time(7, 30)
        data["drop_off_end_time"] = time(19, 0)

        data["drop_off_spacing_mins"] = 45
        data["max_advance_dropoff_days"] = 15
        data["latest_same_day_dropoff_time"] = time(14, 0)
        data["enable_after_hours_dropoff"] = True
        data["after_hours_drop_off_instructions"] = "Updated disclaimer text."

        form = ServiceBookingSettingsForm(data=data, instance=self.service_settings)
        self.assertTrue(form.is_valid(), f"Form not valid for saving: {form.errors}")

        saved_settings = form.save()
        self.assertEqual(saved_settings.booking_advance_notice, 10)
        self.assertEqual(saved_settings.deposit_flat_fee_amount, Decimal("75.00"))
        self.assertEqual(saved_settings.drop_off_start_time, time(7, 30))
        self.assertEqual(saved_settings.drop_off_end_time, time(19, 0))

        self.assertEqual(saved_settings.drop_off_spacing_mins, 45)
        self.assertEqual(saved_settings.max_advance_dropoff_days, 15)
        self.assertEqual(saved_settings.latest_same_day_dropoff_time, time(14, 0))
        self.assertEqual(saved_settings.enable_after_hours_dropoff, True)
        self.assertEqual(
            saved_settings.after_hours_drop_off_instructions, "Updated disclaimer text."
        )

        self.assertEqual(saved_settings.pk, self.service_settings.pk)

    def test_form_valid_drop_off_times(self):
        data = self.valid_data.copy()
        data["drop_off_start_time"] = time(9, 0)
        data["drop_off_end_time"] = time(17, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data["drop_off_start_time"], time(9, 0))
        self.assertEqual(form.cleaned_data["drop_off_end_time"], time(17, 0))

    def test_form_invalid_drop_off_times_start_after_end(self):
        data = self.valid_data.copy()
        data["drop_off_start_time"] = time(17, 0)
        data["drop_off_end_time"] = time(9, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("drop_off_start_time", form.errors)
        self.assertIn(
            "Booking start time must be earlier than end time.",
            form.errors["drop_off_start_time"],
        )
        self.assertIn("drop_off_end_time", form.errors)
        self.assertIn(
            "Booking end time must be earlier than start time.",
            form.errors["drop_off_end_time"],
        )

    def test_form_invalid_drop_off_times_start_equals_end(self):
        data = self.valid_data.copy()
        data["drop_off_start_time"] = time(10, 0)
        data["drop_off_end_time"] = time(10, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("drop_off_start_time", form.errors)
        self.assertIn(
            "Booking start time must be earlier than end time.",
            form.errors["drop_off_start_time"],
        )
        self.assertIn("drop_off_end_time", form.errors)
        self.assertIn(
            "Booking end time must be earlier than start time.",
            form.errors["drop_off_end_time"],
        )

    def test_deposit_calc_method_flat_fee_requires_amount(self):
        data = self.valid_data.copy()
        data["enable_online_deposit"] = True
        data["deposit_calc_method"] = "FLAT_FEE"
        data["deposit_flat_fee_amount"] = ""

        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("deposit_flat_fee_amount", form.errors)
        self.assertIn("This field is required.", form.errors["deposit_flat_fee_amount"])

    def test_deposit_calc_method_percentage_requires_percentage(self):
        data = self.valid_data.copy()
        data["enable_online_deposit"] = True
        data["deposit_calc_method"] = "PERCENTAGE"
        data["deposit_percentage"] = ""

        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("deposit_percentage", form.errors)
        self.assertIn("This field is required.", form.errors["deposit_percentage"])

    def test_booking_open_days_format(self):
        data = self.valid_data.copy()
        data["booking_open_days"] = "Mon,Wed,Fri"
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data["booking_open_days"], "Mon,Wed,Fri")

        data["booking_open_days"] = "Mon, Tue, Wed, Thu, Fri, Sat, Sun"
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(
            form.cleaned_data["booking_open_days"], "Mon, Tue, Wed, Thu, Fri, Sat, Sun"
        )

        data["booking_open_days"] = "invalid-format"
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(
            form.is_valid(), f"Form is not valid with invalid format: {form.errors}"
        )

    def test_drop_off_spacing_mins_valid(self):
        data = self.valid_data.copy()
        data["drop_off_spacing_mins"] = 15
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data["drop_off_spacing_mins"], 15)

    def test_drop_off_spacing_mins_invalid_zero(self):
        data = self.valid_data.copy()
        data["drop_off_spacing_mins"] = 0
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("drop_off_spacing_mins", form.errors)
        self.assertIn(
            "Drop-off spacing must be a positive integer, typically between 1 and 60 minutes.",
            form.errors["drop_off_spacing_mins"],
        )

    def test_drop_off_spacing_mins_invalid_too_high(self):
        data = self.valid_data.copy()
        data["drop_off_spacing_mins"] = 61
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("drop_off_spacing_mins", form.errors)
        self.assertIn(
            "Drop-off spacing must be a positive integer, typically between 1 and 60 minutes.",
            form.errors["drop_off_spacing_mins"],
        )

    def test_max_advance_dropoff_days_valid(self):
        data = self.valid_data.copy()
        data["max_advance_dropoff_days"] = 30
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data["max_advance_dropoff_days"], 30)

    def test_max_advance_dropoff_days_invalid_negative(self):
        data = self.valid_data.copy()
        data["max_advance_dropoff_days"] = -1
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("max_advance_dropoff_days", form.errors)
        self.assertIn(
            "Maximum advance drop-off days cannot be negative.",
            form.errors["max_advance_dropoff_days"],
        )

    def test_latest_same_day_dropoff_time_valid(self):
        data = self.valid_data.copy()
        data["drop_off_start_time"] = time(9, 0)
        data["drop_off_end_time"] = time(17, 0)
        data["latest_same_day_dropoff_time"] = time(12, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

    def test_latest_same_day_dropoff_time_invalid_before_start(self):
        data = self.valid_data.copy()
        data["drop_off_start_time"] = time(9, 0)
        data["drop_off_end_time"] = time(17, 0)
        data["latest_same_day_dropoff_time"] = time(8, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("latest_same_day_dropoff_time", form.errors)
        self.assertIn(
            f"Latest same-day drop-off time must be between {data['drop_off_start_time'].strftime('%H:%M')} and {data['drop_off_end_time'].strftime('%H:%M')}, inclusive.",
            form.errors["latest_same_day_dropoff_time"],
        )

    def test_latest_same_day_dropoff_time_invalid_after_end(self):
        data = self.valid_data.copy()
        data["drop_off_start_time"] = time(9, 0)
        data["drop_off_end_time"] = time(17, 0)
        data["latest_same_day_dropoff_time"] = time(18, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("latest_same_day_dropoff_time", form.errors)
        self.assertIn(
            f"Latest same-day drop-off time must be between {data['drop_off_start_time'].strftime('%H:%M')} and {data['drop_off_end_time'].strftime('%H:%M')}, inclusive.",
            form.errors["latest_same_day_dropoff_time"],
        )
