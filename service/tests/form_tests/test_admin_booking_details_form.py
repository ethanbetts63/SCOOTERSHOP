from django.test import TestCase
from datetime import date, timedelta
from django.utils import timezone
from unittest.mock import patch


from service.forms import AdminBookingDetailsForm
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, TempSalesBookingFactory, SalesProfileFactory, MotorcycleConditionFactory, MotorcycleFactory, MotorcycleImageFactory, FeaturedMotorcycleFactory, InventorySettingsFactory, BlockedSalesDateFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory

class AdminBookingDetailsFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_type = ServiceTypeFactory()

        cls.booking_status_choices = [
            ("pending", "Pending Confirmation"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
            ("completed", "Completed"),
        ]
        cls.payment_status_choices = [
            ("paid", "Paid"),
            ("unpaid", "Unpaid"),
            ("partially_paid", "Partially Paid"),
            ("refunded", "Refunded"),
        ]

        cls._patch_booking_status = patch(
            "service.models.ServiceBooking.BOOKING_STATUS_CHOICES",
            new=cls.booking_status_choices,
        )
        cls._patch_payment_status = patch(
            "service.models.ServiceBooking.PAYMENT_STATUS_CHOICES",
            new=cls.payment_status_choices,
        )
        cls._patch_booking_status.start()
        cls._patch_payment_status.start()

    @classmethod
    def tearDownClass(cls):

        cls._patch_booking_status.stop()
        cls._patch_payment_status.stop()
        super().tearDownClass()

    def test_valid_form_submission(self):

        today = date.today()
        future_date = today + timedelta(days=5)

        current_time = (
            timezone.localtime(timezone.now()) + timedelta(minutes=10)
        ).time()

        form_data = {
            "service_type": self.service_type.pk,
            "service_date": future_date.strftime("%Y-%m-%d"),
            "dropoff_date": future_date.strftime("%Y-%m-%d"),
            "dropoff_time": current_time.strftime("%H:%M"),
            "booking_status": "pending",
            "payment_status": "unpaid",
            "customer_notes": "Please be careful with the paintwork.",
            "admin_notes": "Customer requested a quick turnaround.",
            "estimated_pickup_date": (future_date + timedelta(days=2)).strftime(
                "%Y-%m-%d"
            ),
        }

        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.get_warnings(), [])

    def test_required_fields(self):

        form_data = {}
        form = AdminBookingDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("service_type", form.errors)
        self.assertIn("service_date", form.errors)
        self.assertIn("dropoff_date", form.errors)
        
        self.assertIn("booking_status", form.errors)
        self.assertIn("payment_status", form.errors)
        self.assertIn("estimated_pickup_date", form.errors)

    def test_dropoff_date_after_service_date_warning(self):

        today = date.today()
        service_date = today + timedelta(days=2)
        dropoff_date = today + timedelta(days=5)

        form_data = {
            "service_type": self.service_type.pk,
            "service_date": service_date.strftime("%Y-%m-%d"),
            "dropoff_date": dropoff_date.strftime("%Y-%m-%d"),
            "dropoff_time": "09:00",
            "booking_status": "pending",
            "payment_status": "unpaid",
            "estimated_pickup_date": (service_date + timedelta(days=1)).strftime(
                "%Y-%m-%d"
            ),
        }
        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn(
            "Warning: Drop-off date is after the service date.", form.get_warnings()
        )

    @patch("service.forms.date")
    def test_service_date_in_past_warning(self, mock_date):

        mock_date.today.return_value = date(2025, 1, 15)
        past_service_date = date(2025, 1, 10)

        estimated_pickup_date_val = (past_service_date + timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )

        form_data = {
            "service_type": self.service_type.pk,
            "service_date": past_service_date.strftime("%Y-%m-%d"),
            "dropoff_date": past_service_date.strftime("%Y-%m-%d"),
            "dropoff_time": "09:00",
            "booking_status": "pending",
            "payment_status": "unpaid",
            "estimated_pickup_date": estimated_pickup_date_val,
        }
        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn("Warning: Service date is in the past.", form.get_warnings())

    @patch("service.forms.date")
    def test_dropoff_date_in_past_warning(self, mock_date):

        mock_date.today.return_value = date(2025, 1, 15)
        past_dropoff_date = date(2025, 1, 10)
        future_service_date = date(2025, 1, 20)

        estimated_pickup_date_val = (future_service_date + timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )

        form_data = {
            "service_type": self.service_type.pk,
            "service_date": future_service_date.strftime("%Y-%m-%d"),
            "dropoff_date": past_dropoff_date.strftime("%Y-%m-%d"),
            "dropoff_time": "09:00",
            "booking_status": "pending",
            "payment_status": "unpaid",
            "estimated_pickup_date": estimated_pickup_date_val,
        }
        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn("Warning: Drop-off date is in the past.", form.get_warnings())

    def test_optional_fields_can_be_blank(self):

        today = date.today()
        future_date = today + timedelta(days=5)
        current_time = (
            timezone.localtime(timezone.now()) + timedelta(minutes=10)
        ).time()

        estimated_pickup_date_val = (future_date + timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )

        form_data = {
            "service_type": self.service_type.pk,
            "service_date": future_date.strftime("%Y-%m-%d"),
            "dropoff_date": future_date.strftime("%Y-%m-%d"),
            "dropoff_time": current_time.strftime("%H:%M"),
            "booking_status": "pending",
            "payment_status": "unpaid",
            "estimated_pickup_date": estimated_pickup_date_val,
        }

        form = AdminBookingDetailsForm(data=form_data)

        self.assertTrue(
            form.is_valid(),
            f"Form is not valid when optional fields are blank: {form.errors}",
        )
        self.assertEqual(form.get_warnings(), [])
        self.assertEqual(form.cleaned_data.get("customer_notes"), "")

        self.assertEqual(
            form.cleaned_data.get("estimated_pickup_date"),
            date.fromisoformat(estimated_pickup_date_val),
        )
