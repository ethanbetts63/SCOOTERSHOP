# payments/tests/form_tests/test_refund_settings_form.py

from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from payments.forms import RefundSettingsForm
from payments.models import RefundPolicySettings

class RefundSettingsFormTests(TestCase):
    """
    Tests for the RefundSettingsForm.
    """

    def _get_valid_form_data(self):
        """
        Returns a dictionary representing a valid set of form data for RefundPolicySettings.
        Includes the new sales refund settings.
        """
        return {
            'cancellation_full_payment_full_refund_days': 7,
            'cancellation_full_payment_partial_refund_days': 3,
            'cancellation_full_payment_partial_refund_percentage': Decimal('50.00'),
            'cancellation_full_payment_minimal_refund_days': 1,
            'cancellation_full_payment_minimal_refund_percentage': Decimal('0.00'),
            'cancellation_deposit_full_refund_days': 7,
            'cancellation_deposit_partial_refund_days': 3,
            'cancellation_deposit_partial_refund_percentage': Decimal('50.00'),
            'cancellation_deposit_minimal_refund_days': 1,
            'cancellation_deposit_minimal_refund_percentage': Decimal('0.00'),
            
            # NEW: Sales Refund Settings
            'sales_enable_deposit_refund_grace_period': True,
            'sales_deposit_refund_grace_period_hours': 48, # Example value
            'sales_enable_deposit_refund': True,

            'refund_deducts_stripe_fee_policy': True,
            'stripe_fee_percentage_domestic': Decimal('0.0170'),
            'stripe_fee_fixed_domestic': Decimal('0.30'),
            'stripe_fee_percentage_international': Decimal('0.0350'),
            'stripe_fee_fixed_international': Decimal('0.30'),
        }

    def setUp(self):
        """
        Set up an initial RefundPolicySettings instance for testing,
        as it's designed to be a singleton.
        """
        # Ensure only one instance exists, or create it if none.
        self.refund_settings, created = RefundPolicySettings.objects.get_or_create(pk=1, defaults=self._get_valid_form_data())
        # If it was just created, save it to ensure the save logic (including full_clean) runs
        if created:
            self.refund_settings.save()

    def test_form_valid_data(self):
        """
        Test that the form is valid with correct data, including new sales settings.
        """
        data = self._get_valid_form_data()
        data.update({
            'cancellation_full_payment_full_refund_days': 10,
            'cancellation_full_payment_partial_refund_days': 5,
            'cancellation_full_payment_partial_refund_percentage': Decimal('75.00'),
            'cancellation_full_payment_minimal_refund_days': 2,
            'cancellation_full_payment_minimal_refund_percentage': Decimal('10.00'),
            'cancellation_deposit_full_refund_days': 8,
            'cancellation_deposit_partial_refund_days': 4,
            'cancellation_deposit_partial_refund_percentage': Decimal('60.00'),
            'cancellation_deposit_minimal_refund_days': 1,
            'cancellation_deposit_minimal_refund_percentage': Decimal('5.00'),
            'refund_deducts_stripe_fee_policy': False,
            'stripe_fee_percentage_domestic': Decimal('0.0180'),
            'stripe_fee_fixed_domestic': Decimal('0.40'),
            'stripe_fee_percentage_international': Decimal('0.0360'),
            'stripe_fee_fixed_international': Decimal('0.40'),
            # Update new sales settings
            'sales_enable_deposit_refund_grace_period': False,
            'sales_deposit_refund_grace_period_hours': 72,
            'sales_enable_deposit_refund': False,
        })
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        
        # Save the form and check if the instance is updated
        updated_settings = form.save()
        self.assertEqual(updated_settings.cancellation_full_payment_full_refund_days, 10)
        self.assertEqual(updated_settings.cancellation_full_payment_partial_refund_percentage, Decimal('75.00'))
        self.assertFalse(updated_settings.refund_deducts_stripe_fee_policy)
        self.assertEqual(updated_settings.stripe_fee_percentage_domestic, Decimal('0.0180'))
        # Assert new sales settings
        self.assertFalse(updated_settings.sales_enable_deposit_refund_grace_period)
        self.assertEqual(updated_settings.sales_deposit_refund_grace_period_hours, 72)
        self.assertFalse(updated_settings.sales_enable_deposit_refund)

        self.assertEqual(RefundPolicySettings.objects.count(), 1) # Ensure still only one instance

    def test_form_invalid_percentage_fields(self):
        """
        Test that percentage fields are validated for values outside 0-100%.
        """
        data = self._get_valid_form_data()
        data['cancellation_full_payment_partial_refund_percentage'] = Decimal('101.00') # Invalid
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancellation_full_payment_partial_refund_percentage', form.errors)
        self.assertIn("Ensure cancellation full payment partial refund percentage is between 0.00% and 100.00%.", 
                      form.errors['cancellation_full_payment_partial_refund_percentage'])

        data = self._get_valid_form_data()
        data['cancellation_deposit_minimal_refund_percentage'] = Decimal('-5.00') # Invalid
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancellation_deposit_minimal_refund_percentage', form.errors)
        self.assertIn("Ensure cancellation deposit minimal refund percentage is between 0.00% and 100.00%.", 
                      form.errors['cancellation_deposit_minimal_refund_percentage'])

    def test_form_invalid_stripe_fee_percentage_fields(self):
        """
        Test that Stripe fee percentage fields are validated for sensible rates (e.g., 0-10%).
        """
        data = self._get_valid_form_data()
        data['stripe_fee_percentage_domestic'] = Decimal('0.1500') # Invalid (15%)
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('stripe_fee_percentage_domestic', form.errors)
        self.assertIn("Ensure domestic Stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%).", 
                      form.errors['stripe_fee_percentage_domestic'])
        
        data = self._get_valid_form_data()
        data['stripe_fee_percentage_international'] = Decimal('-0.0100') # Invalid
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('stripe_fee_percentage_international', form.errors)
        self.assertIn("Ensure international Stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%).", 
                      form.errors['stripe_fee_percentage_international'])

    def test_form_invalid_full_payment_days_thresholds(self):
        """
        Test that full payment days thresholds are validated (full >= partial >= minimal).
        """
        # full < partial
        data = self._get_valid_form_data()
        data.update({
            'cancellation_full_payment_full_refund_days': 5,
            'cancellation_full_payment_partial_refund_days': 10, # Invalid
        })
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        # Error is on the specific field
        self.assertIn('cancellation_full_payment_full_refund_days', form.errors)
        self.assertIn("Full refund days must be greater than or equal to partial refund days.", 
                      form.errors['cancellation_full_payment_full_refund_days'][0])

        # partial < minimal
        data = self._get_valid_form_data()
        data.update({
            'cancellation_full_payment_full_refund_days': 10,
            'cancellation_full_payment_partial_refund_days': 5,
            'cancellation_full_payment_minimal_refund_days': 10, # Invalid
        })
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancellation_full_payment_partial_refund_days', form.errors)
        self.assertIn("Partial refund days must be greater than or equal to minimal refund days.", 
                      form.errors['cancellation_full_payment_partial_refund_days'][0])

    def test_form_invalid_deposit_days_thresholds(self):
        """
        Test that deposit days thresholds are validated (full >= partial >= minimal).
        """
        # full < partial
        data = self._get_valid_form_data()
        data.update({
            'cancellation_deposit_full_refund_days': 5,
            'cancellation_deposit_partial_refund_days': 10, # Invalid
        })
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancellation_deposit_full_refund_days', form.errors)
        self.assertIn("Full deposit refund days must be greater than or equal to partial deposit refund days.", 
                      form.errors['cancellation_deposit_full_refund_days'][0])

        # partial < minimal
        data = self._get_valid_form_data()
        data.update({
            'cancellation_deposit_full_refund_days': 10,
            'cancellation_deposit_partial_refund_days': 5,
            'cancellation_deposit_minimal_refund_days': 10, # Invalid
        })
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('cancellation_deposit_partial_refund_days', form.errors)
        self.assertIn("Partial deposit refund days must be greater than or equal to minimal deposit refund days.", 
                      form.errors['cancellation_deposit_partial_refund_days'][0])

    def test_form_no_new_instance_creation(self):
        """
        Test that the form prevents creation of a second instance of RefundPolicySettings
        when form.save() is called.
        """
        # Attempt to create a new instance when one already exists
        data = self._get_valid_form_data()
        form = RefundSettingsForm(data=data) # No instance provided, so it's a new form

        # The form is valid at this stage because the singleton check is in the model's save method
        self.assertTrue(form.is_valid(), f"Form unexpectedly invalid: {form.errors}")
        
        # Expect a ValidationError when trying to save a second instance
        with self.assertRaises(ValidationError) as cm:
            form.save()
        
        # Check the error message
        self.assertIn("Only one instance of RefundPolicySettings can be created. Please edit the existing one.", str(cm.exception))
        
        self.assertEqual(RefundPolicySettings.objects.count(), 1) # Still only one instance

    def test_form_initial_data_for_existing_instance(self):
        """
        Test that the form correctly loads initial data when an instance is provided.
        Includes new sales settings.
        """
        initial_percentage = Decimal('45.00')
        initial_grace_hours = 36
        initial_enable_refund = False

        self.refund_settings.cancellation_full_payment_partial_refund_percentage = initial_percentage
        self.refund_settings.sales_deposit_refund_grace_period_hours = initial_grace_hours
        self.refund_settings.sales_enable_deposit_refund = initial_enable_refund
        self.refund_settings.save()

        form = RefundSettingsForm(instance=self.refund_settings)
        self.assertEqual(form.initial['cancellation_full_payment_partial_refund_percentage'], initial_percentage)
        self.assertEqual(form.initial['sales_deposit_refund_grace_period_hours'], initial_grace_hours)
        self.assertEqual(form.initial['sales_enable_deposit_refund'], initial_enable_refund)

    def test_sales_refund_settings_validation(self):
        """
        Test validation for the new sales refund settings.
        """
        # Test valid data
        data = self._get_valid_form_data()
        data['sales_enable_deposit_refund_grace_period'] = True
        data['sales_deposit_refund_grace_period_hours'] = 24
        data['sales_enable_deposit_refund'] = True
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertTrue(form.is_valid(), f"Form unexpectedly invalid for valid sales settings: {form.errors}")

        # Test invalid grace period hours (e.g., negative)
        data_invalid_hours = self._get_valid_form_data()
        data_invalid_hours['sales_deposit_refund_grace_period_hours'] = -10
        form_invalid_hours = RefundSettingsForm(instance=self.refund_settings, data=data_invalid_hours)
        self.assertFalse(form_invalid_hours.is_valid())
        self.assertIn('sales_deposit_refund_grace_period_hours', form_invalid_hours.errors)
        # FIX: Corrected expected error message to match the custom validation in the model
        self.assertIn('Sales deposit refund grace period hours cannot be negative.', form_invalid_hours.errors['sales_deposit_refund_grace_period_hours'][0])
