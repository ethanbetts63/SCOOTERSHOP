from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta, time
from decimal import Decimal
from inventory.forms.admin_sales_booking_form import AdminSalesBookingForm

from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    SalesProfileFactory,
    MotorcycleFactory,
    InventorySettingsFactory
)


class AdminSalesBookingFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inventory_settings = InventorySettingsFactory(
            deposit_amount=Decimal("100.00")
        )

        cls.sales_profile = SalesProfileFactory()
        cls.motorcycle_available = MotorcycleFactory(
            condition="used", status="for_sale"
        )

        cls.base_valid_data = {
            "booking_status": "confirmed",
            "payment_status": "deposit_paid",
            "amount_paid": "100.00",
            "currency": "AUD",
        }

    def test_form_is_valid_with_complete_and_correct_data(self):
        form_data = {
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "booking_status": "confirmed",
            "payment_status": "deposit_paid",
            "amount_paid": "100.00",
            "currency": "AUD",
            "appointment_date": date.today() + timedelta(days=5),
            "appointment_time": time(14, 30),
            "customer_notes": "This is a test note.",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should be valid, but got errors: {form.errors.as_json()}",
        )

    def test_form_is_invalid_if_profile_id_is_missing(self):
        form_data = {
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "booking_status": "pending_confirmation",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("selected_profile_id", form.errors)
        self.assertEqual(
            form.errors["selected_profile_id"][0], "This field is required."
        )

    def test_form_is_invalid_if_profile_id_does_not_exist(self):
        form_data = {
            "selected_profile_id": 99999,
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "booking_status": "pending_confirmation",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("selected_profile_id", form.errors)
        self.assertEqual(
            form.errors["selected_profile_id"][0],
            "Selected sales profile does not exist.",
        )

    def test_form_is_invalid_if_motorcycle_id_is_missing(self):
        form_data = {
            "selected_profile_id": self.sales_profile.pk,
            "booking_status": "pending_confirmation",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("selected_motorcycle_id", form.errors)
        self.assertEqual(
            form.errors["selected_motorcycle_id"][0], "This field is required."
        )

    def test_form_is_invalid_if_motorcycle_id_does_not_exist(self):
        form_data = {
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": 99999,
            "booking_status": "pending_confirmation",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("selected_motorcycle_id", form.errors)
        self.assertEqual(
            form.errors["selected_motorcycle_id"][0],
            "Selected motorcycle does not exist.",
        )

    def test_warning_is_generated_for_past_appointment_date(self):
        form_data = {
            **self.base_valid_data,
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "appointment_date": date.today() - timedelta(days=1),
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )
        self.assertIn("Warning: Appointment date is in the past.", form.get_warnings())

    def test_warning_is_generated_for_past_appointment_time_on_today(self):
        past_time = (timezone.localtime(timezone.now()) - timedelta(hours=1)).time()
        form_data = {
            **self.base_valid_data,
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "appointment_date": date.today(),
            "appointment_time": past_time,
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )

    def test_warning_for_confirmed_booking_with_unpaid_status(self):
        form_data = {
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "booking_status": "confirmed",
            "payment_status": "unpaid",
            "amount_paid": "0.00",
            "currency": "AUD",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )
        self.assertIn(
            "Warning: Booking is 'Confirmed' but no deposit or full payment recorded. Please verify payment status.",
            form.get_warnings(),
        )

    def test_warning_for_confirmed_booking_with_insufficient_deposit(self):
        insufficient_amount = self.inventory_settings.deposit_amount - Decimal("10.00")
        form_data = {
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": self.motorcycle_available.pk,
            "booking_status": "confirmed",
            "payment_status": "deposit_paid",
            "amount_paid": str(insufficient_amount),
            "currency": "AUD",
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )
        expected_warning = (
            f"Warning: Booking is 'Confirmed' but recorded amount paid "
            f"(${insufficient_amount}) is less than the required deposit "
            f"(${self.inventory_settings.deposit_amount})."
        )
        self.assertIn(expected_warning, form.get_warnings())

    def test_warning_for_used_motorcycle_that_is_already_reserved(self):
        reserved_bike = MotorcycleFactory(condition="used", status="reserved")
        form_data = {
            **self.base_valid_data,
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": reserved_bike.pk,
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )
        expected_warning = f"Warning: The selected motorcycle '{reserved_bike.title}' is currently 'Reserved'. Confirm this is acceptable."
        self.assertIn(expected_warning, form.get_warnings())

    def test_no_warning_when_editing_booking_for_its_own_reserved_motorcycle(self):
        reserved_bike = MotorcycleFactory(condition="used", status="for_sale")
        booking_instance = SalesBookingFactory(
            motorcycle=reserved_bike,
            sales_profile=self.sales_profile,
            booking_status="confirmed",
        )
        reserved_bike.status = "reserved"
        reserved_bike.save()

        form_data = {
            "selected_profile_id": booking_instance.sales_profile.pk,
            "selected_motorcycle_id": booking_instance.motorcycle.pk,
            "booking_status": "confirmed",
            "payment_status": booking_instance.payment_status,
            "amount_paid": booking_instance.amount_paid,
            "currency": booking_instance.currency,
        }
        form = AdminSalesBookingForm(data=form_data, instance=booking_instance)

        self.assertTrue(
            form.is_valid(),
            f"Form should be valid but had errors: {form.errors.as_json()}",
        )

    def test_warning_for_new_motorcycle_out_of_stock(self):
        out_of_stock_bike = MotorcycleFactory(
            condition="new", quantity=0, status="for_sale"
        )
        form_data = {
            **self.base_valid_data,
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": out_of_stock_bike.pk,
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )
        expected_warning = f"Warning: The selected new motorcycle '{out_of_stock_bike.title}' is currently out of stock (quantity 0)."
        self.assertIn(expected_warning, form.get_warnings())

    def test_warning_for_new_motorcycle_with_only_one_left(self):
        last_bike_in_stock = MotorcycleFactory(
            condition="new", quantity=1, status="for_sale"
        )
        form_data = {
            **self.base_valid_data,
            "selected_profile_id": self.sales_profile.pk,
            "selected_motorcycle_id": last_bike_in_stock.pk,
        }
        form = AdminSalesBookingForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should have been valid but had errors: {form.errors.as_json()}",
        )
        expected_warning = (
            f"Warning: The selected new motorcycle '{last_bike_in_stock.title}' has only 1 unit remaining. "
            f"Confirming this booking will make it out of stock."
        )
        self.assertIn(expected_warning, form.get_warnings())

    def test_form_initializes_correctly_from_instance(self):
        booking_instance = SalesBookingFactory(
            sales_profile=self.sales_profile, motorcycle=self.motorcycle_available
        )
        form = AdminSalesBookingForm(instance=booking_instance)

        self.assertEqual(
            form.fields["selected_profile_id"].initial, self.sales_profile.pk
        )
        self.assertEqual(
            form.fields["selected_motorcycle_id"].initial, self.motorcycle_available.pk
        )

        self.assertEqual(
            form.initial.get("booking_status"), booking_instance.booking_status
        )
        self.assertEqual(
            form.initial.get("customer_notes"), booking_instance.customer_notes
        )
