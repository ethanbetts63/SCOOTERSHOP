from django.test import TestCase
from datetime import date, time, timedelta
import datetime
from django.utils import timezone
from unittest.mock import patch, Mock

# Import the form to be tested
from service.forms import AdminBookingDetailsForm

# Import factories for ServiceType (needed for ModelChoiceField queryset)
from ..test_helpers.model_factories import ServiceTypeFactory, ServiceBookingFactory

class AdminBookingDetailsFormTest(TestCase):
    """
    Tests for the AdminBookingDetailsForm.
    Focuses on field validation and custom clean method warning logic.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that will not be modified during tests.
        Create a ServiceType instance needed for the form's queryset.
        """
        cls.service_type = ServiceTypeFactory()

        cls.booking_status_choices = [
            ('pending', 'Pending Confirmation'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
            ('completed', 'Completed'),
        ]
        cls.payment_status_choices = [
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
            ('partially_paid', 'Partially Paid'),
            ('refunded', 'Refunded'),
        ]

        # Patch the choices if they are fetched dynamically from the model
        cls._patch_booking_status = patch('service.models.ServiceBooking.BOOKING_STATUS_CHOICES', new=cls.booking_status_choices)
        cls._patch_payment_status = patch('service.models.ServiceBooking.PAYMENT_STATUS_CHOICES', new=cls.payment_status_choices)
        cls._patch_booking_status.start()
        cls._patch_payment_status.start()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up patches after all tests are done.
        """
        cls._patch_booking_status.stop()
        cls._patch_payment_status.stop()
        super().tearDownClass()

    def test_valid_form_submission(self):
        """
        Test a form submission with all valid data and no warnings.
        """
        today = date.today()
        future_date = today + timedelta(days=5)
        # Ensure current_time is definitely in the future for today's date
        current_time = (timezone.localtime(timezone.now()) + timedelta(minutes=10)).time()

        form_data = {
            'service_type': self.service_type.pk,
            'service_date': future_date.strftime('%Y-%m-%d'),
            'dropoff_date': future_date.strftime('%Y-%m-%d'),
            'dropoff_time': current_time.strftime('%H:%M'),
            'booking_status': 'pending',
            'payment_status': 'unpaid',
            'customer_notes': 'Please be careful with the paintwork.',
            'admin_notes': 'Customer requested a quick turnaround.',
            'estimated_pickup_date': (future_date + timedelta(days=2)).strftime('%Y-%m-%d'),
        }

        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.get_warnings(), [])


    def test_required_fields(self):
        """
        Test that required fields are correctly marked as required.
        """
        form_data = {} # Empty data
        form = AdminBookingDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('service_date', form.errors)
        self.assertIn('dropoff_date', form.errors)
        self.assertIn('dropoff_time', form.errors)
        self.assertIn('booking_status', form.errors)
        self.assertIn('payment_status', form.errors)
        self.assertIn('estimated_pickup_date', form.errors) # Now required


    def test_dropoff_date_after_service_date_warning(self):
        """
        Test warning: Drop-off date is after the service date.
        """
        today = date.today()
        service_date = today + timedelta(days=2)
        dropoff_date = today + timedelta(days=5) # Drop-off after service

        form_data = {
            'service_type': self.service_type.pk,
            'service_date': service_date.strftime('%Y-%m-%d'),
            'dropoff_date': dropoff_date.strftime('%Y-%m-%d'),
            'dropoff_time': '09:00',
            'booking_status': 'pending',
            'payment_status': 'unpaid',
            'estimated_pickup_date': (service_date + timedelta(days=1)).strftime('%Y-%m-%d'), # Added
        }
        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn("Warning: Drop-off date is after the service date.", form.get_warnings())

    @patch('service.forms.date') # Patch datetime.date in the form's module
    def test_service_date_in_past_warning(self, mock_date):
        """
        Test warning: Service date is in the past.
        """
        mock_date.today.return_value = date(2025, 1, 15) # Fix today's date for consistent test
        past_service_date = date(2025, 1, 10)
        # Estimated pickup date should be after the service date
        estimated_pickup_date_val = (past_service_date + timedelta(days=1)).strftime('%Y-%m-%d')

        form_data = {
            'service_type': self.service_type.pk,
            'service_date': past_service_date.strftime('%Y-%m-%d'),
            'dropoff_date': past_service_date.strftime('%Y-%m-%d'),
            'dropoff_time': '09:00',
            'booking_status': 'pending',
            'payment_status': 'unpaid',
            'estimated_pickup_date': estimated_pickup_date_val, # Added
        }
        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn("Warning: Service date is in the past.", form.get_warnings())

    @patch('service.forms.date') # Patch datetime.date in the form's module
    def test_dropoff_date_in_past_warning(self, mock_date):
        """
        Test warning: Drop-off date is in the past.
        """
        mock_date.today.return_value = date(2025, 1, 15) # Fix today's date
        past_dropoff_date = date(2025, 1, 10)
        future_service_date = date(2025, 1, 20) # Future service date
        # Estimated pickup date should be after the service date
        estimated_pickup_date_val = (future_service_date + timedelta(days=1)).strftime('%Y-%m-%d')

        form_data = {
            'service_type': self.service_type.pk,
            'service_date': future_service_date.strftime('%Y-%m-%d'),
            'dropoff_date': past_dropoff_date.strftime('%Y-%m-%d'),
            'dropoff_time': '09:00',
            'booking_status': 'pending',
            'payment_status': 'unpaid',
            'estimated_pickup_date': estimated_pickup_date_val, # Added
        }
        form = AdminBookingDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn("Warning: Drop-off date is in the past.", form.get_warnings())

    def test_optional_fields_can_be_blank(self):
        """
        Test that optional fields (customer_notes, admin_notes)
        can be left blank without causing validation errors,
        while estimated_pickup_date is correctly provided.
        """
        today = date.today()
        future_date = today + timedelta(days=5)
        current_time = (timezone.localtime(timezone.now()) + timedelta(minutes=10)).time()
        
        # estimated_pickup_date is now required, so it must be included
        estimated_pickup_date_val = (future_date + timedelta(days=1)).strftime('%Y-%m-%d')

        form_data = {
            'service_type': self.service_type.pk,
            'service_date': future_date.strftime('%Y-%m-%d'),
            'dropoff_date': future_date.strftime('%Y-%m-%d'),
            'dropoff_time': current_time.strftime('%H:%M'),
            'booking_status': 'pending',
            'payment_status': 'unpaid',
            'estimated_pickup_date': estimated_pickup_date_val, # Now explicitly included
            # customer_notes, admin_notes are still omitted (blank)
        }

        form = AdminBookingDetailsForm(data=form_data)
        # The form should now be valid as estimated_pickup_date is provided
        self.assertTrue(form.is_valid(), f"Form is not valid when optional fields are blank: {form.errors}")
        self.assertEqual(form.get_warnings(), [])
        self.assertEqual(form.cleaned_data.get('customer_notes'), '')
        # estimated_pickup_date should now have a value, not None
        self.assertEqual(form.cleaned_data.get('estimated_pickup_date'), date.fromisoformat(estimated_pickup_date_val))

