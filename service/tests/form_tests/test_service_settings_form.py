from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import time # Import time for test data

from service.forms import ServiceBookingSettingsForm
from service.models import ServiceSettings
from ..test_helpers.model_factories import ServiceSettingsFactory

class ServiceBookingSettingsFormTest(TestCase):
    """
    Tests for the ServiceBookingSettingsForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create a ServiceSettings instance using the factory.
        The factory ensures a singleton, so we'll always get/update the same one.
        """
        cls.service_settings = ServiceSettingsFactory()

        # Define a set of valid data for the form
        cls.valid_data = {
            'enable_service_booking': True,
            'booking_advance_notice': 1,
            'max_visible_slots_per_day': 6,
            'allow_anonymous_bookings': True,
            'allow_account_bookings': True,
            'booking_open_days': 'Mon,Tue,Wed,Thu,Fri',
            'drop_off_start_time': time(9, 0),
            'drop_off_end_time': time(17, 0),
            'enable_service_brands': True,
            'other_brand_policy_text': 'Policy for other brands.',
            'enable_deposit': True,
            'deposit_calc_method': 'FLAT_FEE',
            'deposit_flat_fee_amount': Decimal('25.00'),
            'deposit_percentage': Decimal('0.00'), # Should be 0 if flat fee
            'enable_online_full_payment': True,
            'enable_online_deposit': True,
            'enable_instore_full_payment': True,
            'currency_code': 'AUD',
            'currency_symbol': '$',
            'cancel_full_payment_max_refund_days': 7,
            'cancel_full_payment_max_refund_percentage': Decimal('1.00'),
            'cancel_full_payment_partial_refund_days': 3,
            'cancel_full_payment_partial_refund_percentage': Decimal('0.50'),
            'cancel_full_payment_min_refund_days': 1,
            'cancel_full_payment_min_refund_percentage': Decimal('0.00'),
            'cancel_deposit_max_refund_days': 7,
            'cancel_deposit_max_refund_percentage': Decimal('1.00'),
            'cancel_deposit_partial_refund_days': 3,
            'cancel_deposit_partial_refund_percentage': Decimal('0.50'),
            'cancel_deposit_min_refund_days': 1,
            'cancel_deposit_min_refund_percentage': Decimal('0.00'),
            'refund_deducts_stripe_fee_policy': True,
            'stripe_fee_percentage_domestic': Decimal('0.0170'),
            'stripe_fee_fixed_domestic': Decimal('0.30'),
            'stripe_fee_percentage_international': Decimal('0.0350'),
            'stripe_fee_fixed_international': Decimal('0.30'),
        }

    def test_form_valid_data(self):
        """
        Test that the form is valid with complete and correct data.
        """
        form = ServiceBookingSettingsForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        # Verify cleaned data types for Decimal fields
        self.assertIsInstance(form.cleaned_data['deposit_flat_fee_amount'], Decimal)
        self.assertIsInstance(form.cleaned_data['deposit_percentage'], Decimal)
        self.assertIsInstance(form.cleaned_data['stripe_fee_percentage_domestic'], Decimal)
        # Verify cleaned data types for Time fields
        self.assertIsInstance(form.cleaned_data['drop_off_start_time'], time)
        self.assertIsInstance(form.cleaned_data['drop_off_end_time'], time)


    def test_form_initialization_with_instance(self):
        """
        Test that the form correctly loads data from an existing instance.
        """
        # Update the existing singleton instance with specific values
        self.service_settings.enable_service_booking = False
        self.service_settings.booking_advance_notice = 5
        self.service_settings.deposit_flat_fee_amount = Decimal('100.00')
        self.service_settings.drop_off_start_time = time(8, 0)
        self.service_settings.drop_off_end_time = time(18, 0)
        self.service_settings.save() # Save changes to the instance

        form = ServiceBookingSettingsForm(instance=self.service_settings)
        self.assertEqual(form.initial['enable_service_booking'], False)
        self.assertEqual(form.initial['booking_advance_notice'], 5)
        self.assertEqual(form.initial['deposit_flat_fee_amount'], Decimal('100.00'))
        self.assertEqual(form.initial['drop_off_start_time'], time(8, 0))
        self.assertEqual(form.initial['drop_off_end_time'], time(18, 0))

    def test_form_save_updates_instance(self):
        """
        Test that saving the form updates the ServiceSettings instance.
        """
        data = self.valid_data.copy()
        data['enable_service_booking'] = False
        data['booking_advance_notice'] = 10
        data['deposit_flat_fee_amount'] = Decimal('75.00')
        data['drop_off_start_time'] = time(7, 30)
        data['drop_off_end_time'] = time(19, 0)


        form = ServiceBookingSettingsForm(data=data, instance=self.service_settings)
        self.assertTrue(form.is_valid(), f"Form not valid for saving: {form.errors}")
        
        saved_settings = form.save()
        self.assertEqual(saved_settings.enable_service_booking, False)
        self.assertEqual(saved_settings.booking_advance_notice, 10)
        self.assertEqual(saved_settings.deposit_flat_fee_amount, Decimal('75.00'))
        self.assertEqual(saved_settings.drop_off_start_time, time(7, 30))
        self.assertEqual(saved_settings.drop_off_end_time, time(19, 0))
        # Ensure it's the same singleton instance
        self.assertEqual(saved_settings.pk, self.service_settings.pk)

    # --- Validation Tests for Percentage Fields ---
    def test_form_invalid_general_percentage_fields(self):
        """
        Test validation for general percentage fields (0.00 to 1.00).
        """
        percentage_fields = [
            'deposit_percentage',
            'cancel_full_payment_max_refund_percentage',
            'cancel_full_payment_partial_refund_percentage',
            'cancel_full_payment_min_refund_percentage',
            'cancel_deposit_max_refund_percentage',
            'cancel_deposit_partial_refund_percentage',
            'cancel_deposit_min_refund_percentage',
        ]
        for field_name in percentage_fields:
            with self.subTest(f"Invalid {field_name} (too high)"):
                data = self.valid_data.copy()
                data[field_name] = Decimal('1.01') # Too high
                form = ServiceBookingSettingsForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)
                self.assertIn(f"Ensure {field_name.replace('_', ' ')} is between 0.00 (0%) and 1.00 (100%).", form.errors[field_name])

            with self.subTest(f"Invalid {field_name} (too low)"):
                data = self.valid_data.copy()
                data[field_name] = Decimal('-0.01') # Too low
                form = ServiceBookingSettingsForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)
                self.assertIn(f"Ensure {field_name.replace('_', ' ')} is between 0.00 (0%) and 1.00 (100%).", form.errors[field_name])

    def test_form_invalid_stripe_fee_percentage_fields(self):
        """
        Test validation for Stripe fee percentage fields (0.00 to 0.10).
        """
        stripe_fields = [
            'stripe_fee_percentage_domestic',
            'stripe_fee_percentage_international',
        ]
        for field_name in stripe_fields:
            with self.subTest(f"Invalid {field_name} (too high)"):
                data = self.valid_data.copy()
                data[field_name] = Decimal('0.11') # Too high
                form = ServiceBookingSettingsForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)
                self.assertIn("Ensure domestic stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)." if 'domestic' in field_name else "Ensure international stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%).", form.errors[field_name])

            with self.subTest(f"Invalid {field_name} (too low)"):
                data = self.valid_data.copy()
                data[field_name] = Decimal('-0.0001') # Too low
                form = ServiceBookingSettingsForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)
                self.assertIn("Ensure domestic stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)." if 'domestic' in field_name else "Ensure international stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%).", form.errors[field_name])

    # --- Validation Tests for Refund Days Order ---
    def test_form_invalid_full_payment_refund_days_order(self):
        """
        Test validation for full payment refund days order (max >= partial >= min).
        """
        # max < partial
        data = self.valid_data.copy()
        data['cancel_full_payment_max_refund_days'] = 2
        data['cancel_full_payment_partial_refund_days'] = 3
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancel_full_payment_max_refund_days', form.errors)
        self.assertIn("Max refund days must be greater than or equal to partial refund days.", form.errors['cancel_full_payment_max_refund_days'])

        # partial < min
        data = self.valid_data.copy()
        data['cancel_full_payment_partial_refund_days'] = 0
        data['cancel_full_payment_min_refund_days'] = 1
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancel_full_payment_partial_refund_days', form.errors)
        self.assertIn("Partial refund days must be greater than or equal to min refund days.", form.errors['cancel_full_payment_partial_refund_days'])

    def test_form_invalid_deposit_refund_days_order(self):
        """
        Test validation for deposit refund days order (max >= partial >= min).
        """
        # max < partial
        data = self.valid_data.copy()
        data['cancel_deposit_max_refund_days'] = 2
        data['cancel_deposit_partial_refund_days'] = 3
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancel_deposit_max_refund_days', form.errors)
        self.assertIn("Max deposit refund days must be greater than or equal to partial deposit refund days.", form.errors['cancel_deposit_max_refund_days'])

        # partial < min
        data = self.valid_data.copy()
        data['cancel_deposit_partial_refund_days'] = 0
        data['cancel_deposit_min_refund_days'] = 1
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancel_deposit_partial_refund_days', form.errors)
        self.assertIn("Partial deposit refund days must be greater than or equal to min deposit refund days.", form.errors['cancel_deposit_partial_refund_days'])

    def test_form_valid_refund_days_order(self):
        """
        Test valid refund days order (max >= partial >= min).
        """
        data = self.valid_data.copy()
        # All equal
        data['cancel_full_payment_max_refund_days'] = 5
        data['cancel_full_payment_partial_refund_days'] = 5
        data['cancel_full_payment_min_refund_days'] = 5
        # Decreasing
        data['cancel_deposit_max_refund_days'] = 10
        data['cancel_deposit_partial_refund_days'] = 5
        data['cancel_deposit_min_refund_days'] = 0
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

    # --- New Tests for drop_off_start_time and drop_off_end_time ---
    def test_form_valid_drop_off_times(self):
        """
        Test that the form is valid with correct drop-off start and end times.
        """
        data = self.valid_data.copy()
        data['drop_off_start_time'] = time(9, 0)
        data['drop_off_end_time'] = time(17, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['drop_off_start_time'], time(9, 0))
        self.assertEqual(form.cleaned_data['drop_off_end_time'], time(17, 0))

    def test_form_invalid_drop_off_times_start_after_end(self):
        """
        Test that the form is invalid if drop_off_start_time is after drop_off_end_time.
        """
        data = self.valid_data.copy()
        data['drop_off_start_time'] = time(17, 0)
        data['drop_off_end_time'] = time(9, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('drop_off_start_time', form.errors)
        self.assertIn('Booking start time must be earlier than end time.', form.errors['drop_off_start_time'])
        self.assertIn('drop_off_end_time', form.errors)
        self.assertIn('Booking end time must be earlier than start time.', form.errors['drop_off_end_time'])

    def test_form_invalid_drop_off_times_start_equals_end(self):
        """
        Test that the form is invalid if drop_off_start_time is equal to drop_off_end_time.
        """
        data = self.valid_data.copy()
        data['drop_off_start_time'] = time(10, 0)
        data['drop_off_end_time'] = time(10, 0)
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('drop_off_start_time', form.errors)
        self.assertIn('Booking start time must be earlier than end time.', form.errors['drop_off_start_time'])
        self.assertIn('drop_off_end_time', form.errors)
        self.assertIn('Booking end time must be earlier than start time.', form.errors['drop_off_end_time'])

    # --- Conditional Validation Tests ---
    def test_deposit_calc_method_flat_fee_requires_amount(self):
        """
        Test that if deposit_calc_method is FLAT_FEE, deposit_flat_fee_amount is required.
        """
        data = self.valid_data.copy()
        data['enable_deposit'] = True
        data['deposit_calc_method'] = 'FLAT_FEE'
        data['deposit_flat_fee_amount'] = '' # Empty flat fee amount, should cause "required" error

        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid()) # Expecting form to be invalid
        self.assertIn('deposit_flat_fee_amount', form.errors)
        self.assertIn('This field is required.', form.errors['deposit_flat_fee_amount'])


    def test_deposit_calc_method_percentage_requires_percentage(self):
        """
        Test that if deposit_calc_method is PERCENTAGE, deposit_percentage is required.
        """
        data = self.valid_data.copy()
        data['enable_deposit'] = True
        data['deposit_calc_method'] = 'PERCENTAGE'
        data['deposit_percentage'] = '' # Empty percentage, should cause "required" error

        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid()) # Expecting form to be invalid
        self.assertIn('deposit_percentage', form.errors)
        self.assertIn('This field is required.', form.errors['deposit_percentage'])

    def test_booking_open_days_format(self):
        """
        Test that booking_open_days accepts comma-separated string.
        """
        data = self.valid_data.copy()
        data['booking_open_days'] = 'Mon,Wed,Fri'
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['booking_open_days'], 'Mon,Wed,Fri')

        data['booking_open_days'] = 'Mon, Tue, Wed, Thu, Fri, Sat, Sun'
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['booking_open_days'], 'Mon, Tue, Wed, Thu, Fri, Sat, Sun')

        # No specific format validation is in the model, so any string should pass form validation
        data['booking_open_days'] = 'invalid-format'
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid with invalid format: {form.errors}")

