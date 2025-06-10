from django.test import TestCase
from decimal import Decimal
from datetime import time
from django.utils.translation import gettext_lazy as _

from service.forms import ServiceBookingSettingsForm
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

        # Define a set of valid data for the form, excluding removed fields
        cls.valid_data = {
            'enable_service_booking': True,
            'booking_advance_notice': 1,
            'max_visible_slots_per_day': 6,
            'allow_anonymous_bookings': True,
            'allow_account_bookings': True,
            'booking_open_days': 'Mon,Tue,Wed,Thu,Fri',
            'drop_off_start_time': time(9, 0),
            'drop_off_end_time': time(17, 0),
            'drop_off_spacing_mins': 30,
            'max_advance_dropoff_days': 7,
            'latest_same_day_dropoff_time': time(12, 0),
            'allow_after_hours_dropoff': False,
            'after_hours_dropoff_disclaimer': 'Motorcycle drop-off outside of opening hours is at your own risk.',
            'enable_service_brands': True,
            'other_brand_policy_text': 'Policy for other brands.',
            'enable_deposit': True,
            'deposit_calc_method': 'FLAT_FEE',
            'deposit_flat_fee_amount': Decimal('25.00'),
            'deposit_percentage': Decimal('0.00'), # Should be 0 if flat fee, or relevant percentage if method is 'PERCENTAGE'
            'enable_online_full_payment': True,
            'enable_online_deposit': True,
            'enable_instore_full_payment': True,
            'currency_code': 'AUD',
            'currency_symbol': '$',
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
        # Verify cleaned data types for Time fields
        self.assertIsInstance(form.cleaned_data['drop_off_start_time'], time)
        self.assertIsInstance(form.cleaned_data['drop_off_end_time'], time)
        self.assertIsInstance(form.cleaned_data['latest_same_day_dropoff_time'], time)

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
        # Set new fields for the instance to match the updated model
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.max_advance_dropoff_days = 10
        self.service_settings.latest_same_day_dropoff_time = time(13, 0)
        self.service_settings.allow_after_hours_dropoff = True
        self.service_settings.after_hours_dropoff_disclaimer = 'Test disclaimer.'

        self.service_settings.save() # Save changes to the instance

        form = ServiceBookingSettingsForm(instance=self.service_settings)
        self.assertEqual(form.initial['enable_service_booking'], False)
        self.assertEqual(form.initial['booking_advance_notice'], 5)
        self.assertEqual(form.initial['deposit_flat_fee_amount'], Decimal('100.00'))
        self.assertEqual(form.initial['drop_off_start_time'], time(8, 0))
        self.assertEqual(form.initial['drop_off_end_time'], time(18, 0))
        # Assert new fields are loaded correctly
        self.assertEqual(form.initial['drop_off_spacing_mins'], 60)
        self.assertEqual(form.initial['max_advance_dropoff_days'], 10)
        self.assertEqual(form.initial['latest_same_day_dropoff_time'], time(13, 0))
        self.assertEqual(form.initial['allow_after_hours_dropoff'], True)
        self.assertEqual(form.initial['after_hours_dropoff_disclaimer'], 'Test disclaimer.')

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
        # Update new fields for saving
        data['drop_off_spacing_mins'] = 45
        data['max_advance_dropoff_days'] = 15
        data['latest_same_day_dropoff_time'] = time(14, 0)
        data['allow_after_hours_dropoff'] = True
        data['after_hours_dropoff_disclaimer'] = 'Updated disclaimer text.'

        form = ServiceBookingSettingsForm(data=data, instance=self.service_settings)
        self.assertTrue(form.is_valid(), f"Form not valid for saving: {form.errors}")
        
        saved_settings = form.save()
        self.assertEqual(saved_settings.enable_service_booking, False)
        self.assertEqual(saved_settings.booking_advance_notice, 10)
        self.assertEqual(saved_settings.deposit_flat_fee_amount, Decimal('75.00'))
        self.assertEqual(saved_settings.drop_off_start_time, time(7, 30))
        self.assertEqual(saved_settings.drop_off_end_time, time(19, 0))
        # Assert new fields are updated correctly
        self.assertEqual(saved_settings.drop_off_spacing_mins, 45)
        self.assertEqual(saved_settings.max_advance_dropoff_days, 15)
        self.assertEqual(saved_settings.latest_same_day_dropoff_time, time(14, 0))
        self.assertEqual(saved_settings.allow_after_hours_dropoff, True)
        self.assertEqual(saved_settings.after_hours_dropoff_disclaimer, 'Updated disclaimer text.')

        # Ensure it's the same singleton instance
        self.assertEqual(saved_settings.pk, self.service_settings.pk)

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

    # New tests for drop_off_spacing_mins
    def test_drop_off_spacing_mins_valid(self):
        """Test valid values for drop_off_spacing_mins."""
        data = self.valid_data.copy()
        data['drop_off_spacing_mins'] = 15
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['drop_off_spacing_mins'], 15)

    def test_drop_off_spacing_mins_invalid_zero(self):
        """Test invalid value (zero) for drop_off_spacing_mins."""
        data = self.valid_data.copy()
        data['drop_off_spacing_mins'] = 0
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('drop_off_spacing_mins', form.errors)
        self.assertIn("Drop-off spacing must be a positive integer, typically between 1 and 60 minutes.", form.errors['drop_off_spacing_mins'])

    def test_drop_off_spacing_mins_invalid_too_high(self):
        """Test invalid value (greater than 60) for drop_off_spacing_mins."""
        data = self.valid_data.copy()
        data['drop_off_spacing_mins'] = 61
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('drop_off_spacing_mins', form.errors)
        self.assertIn("Drop-off spacing must be a positive integer, typically between 1 and 60 minutes.", form.errors['drop_off_spacing_mins'])

    # New tests for max_advance_dropoff_days
    def test_max_advance_dropoff_days_valid(self):
        """Test valid values for max_advance_dropoff_days."""
        data = self.valid_data.copy()
        data['max_advance_dropoff_days'] = 30
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['max_advance_dropoff_days'], 30)

    def test_max_advance_dropoff_days_invalid_negative(self):
        """Test invalid value (negative) for max_advance_dropoff_days."""
        data = self.valid_data.copy()
        data['max_advance_dropoff_days'] = -1
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('max_advance_dropoff_days', form.errors)
        self.assertIn("Maximum advance drop-off days cannot be negative.", form.errors['max_advance_dropoff_days'])

    # New test for latest_same_day_dropoff_time validation
    def test_latest_same_day_dropoff_time_valid(self):
        """
        Test that latest_same_day_dropoff_time is valid when within the drop-off time range.
        """
        data = self.valid_data.copy()
        data['drop_off_start_time'] = time(9, 0)
        data['drop_off_end_time'] = time(17, 0)
        data['latest_same_day_dropoff_time'] = time(12, 0) # Within range
        form = ServiceBookingSettingsForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

    def test_latest_same_day_dropoff_time_invalid_before_start(self):
        """
        Test that latest_same_day_dropoff_time is invalid when before drop_off_start_time.
        """
        data = self.valid_data.copy()
        data['drop_off_start_time'] = time(9, 0)
        data['drop_off_end_time'] = time(17, 0)
        data['latest_same_day_dropoff_time'] = time(8, 0) # Before start time
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('latest_same_day_dropoff_time', form.errors)
        self.assertIn(f"Latest same-day drop-off time must be between {data['drop_off_start_time'].strftime('%H:%M')} and {data['drop_off_end_time'].strftime('%H:%M')}, inclusive.", form.errors['latest_same_day_dropoff_time'])

    def test_latest_same_day_dropoff_time_invalid_after_end(self):
        """
        Test that latest_same_day_dropoff_time is invalid when after drop_off_end_time.
        """
        data = self.valid_data.copy()
        data['drop_off_start_time'] = time(9, 0)
        data['drop_off_end_time'] = time(17, 0)
        data['latest_same_day_dropoff_time'] = time(18, 0) # After end time
        form = ServiceBookingSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('latest_same_day_dropoff_time', form.errors)
        self.assertIn(f"Latest same-day drop-off time must be between {data['drop_off_start_time'].strftime('%H:%M')} and {data['drop_off_end_time'].strftime('%H:%M')}, inclusive.", form.errors['latest_same_day_dropoff_time'])

