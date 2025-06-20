# payments/tests/model_tests/test_refund_policy_settings.py

from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from payments.models import RefundPolicySettings

class RefundPolicySettingsModelTests(TestCase):
    """
    Tests for the RefundPolicySettings model.
    """

    def setUp(self):
        """
        Set up test data by ensuring the RefundPolicySettings instance is
        deleted before each test to guarantee a clean slate for singleton tests.
        """
        RefundPolicySettings.objects.all().delete()
        # Create a default instance for most tests
        self.settings = RefundPolicySettings.objects.create()

    def test_singleton_creation_raises_error(self):
        """
        Test that attempting to create a second instance of RefundPolicySettings
        raises a ValidationError.
        """
        # Ensure only one instance exists initially from setUp
        self.assertEqual(RefundPolicySettings.objects.count(), 1)

        # Expect a ValidationError when trying to create a second instance
        with self.assertRaises(ValidationError) as context:
            RefundPolicySettings.objects.create(
                cancellation_full_payment_full_refund_days=10
            )

        # Verify the error message is what we expect
        self.assertIn(
            "Only one instance of RefundPolicySettings can be created.",
            str(context.exception)
        )

        # Ensure no new instance was created
        self.assertEqual(RefundPolicySettings.objects.count(), 1)

    def test_singleton_get_or_create(self):
        """
        Test that get_or_create retrieves the existing singleton instance
        instead of creating a new one.
        """
        self.assertEqual(RefundPolicySettings.objects.count(), 1)
        initial_instance = RefundPolicySettings.objects.get()

        # get_or_create should not create a new object
        new_settings, created = RefundPolicySettings.objects.get_or_create(pk=1)

        # Check that no new instance was created
        self.assertFalse(created)
        self.assertEqual(RefundPolicySettings.objects.count(), 1)
        self.assertEqual(new_settings.pk, initial_instance.pk)


    def test_default_values(self):
        """
        Test that default values are correctly applied upon creation.
        """
        # Delete existing to ensure a fresh creation with defaults
        RefundPolicySettings.objects.all().delete()
        settings = RefundPolicySettings.objects.create()

        # Full Payment Policy Defaults
        self.assertEqual(settings.cancellation_full_payment_full_refund_days, 7)
        self.assertEqual(settings.cancellation_full_payment_partial_refund_days, 3)
        self.assertEqual(settings.cancellation_full_payment_partial_refund_percentage, Decimal('50.00'))
        self.assertEqual(settings.cancellation_full_payment_minimal_refund_days, 1)
        self.assertEqual(settings.cancellation_full_payment_minimal_refund_percentage, Decimal('0.00'))

        # Deposit Policy Defaults
        self.assertEqual(settings.cancellation_deposit_full_refund_days, 7)
        self.assertEqual(settings.cancellation_deposit_partial_refund_days, 3)
        self.assertEqual(settings.cancellation_deposit_partial_refund_percentage, Decimal('50.00'))
        self.assertEqual(settings.cancellation_deposit_minimal_refund_days, 1)
        self.assertEqual(settings.cancellation_deposit_minimal_refund_percentage, Decimal('0.00'))

        # Stripe Fee Defaults
        self.assertTrue(settings.refund_deducts_stripe_fee_policy)
        self.assertEqual(settings.stripe_fee_percentage_domestic, Decimal('0.0170'))
        self.assertEqual(settings.stripe_fee_fixed_domestic, Decimal('0.30'))
        self.assertEqual(settings.stripe_fee_percentage_international, Decimal('0.0350'))
        self.assertEqual(settings.stripe_fee_fixed_international, Decimal('0.30'))

    def test_str_method(self):
        """
        Test the __str__ method of the model.
        """
        self.assertEqual(str(self.settings), "Refund Policy Settings")

    # --- Validation Tests for clean() method ---

    def test_percentage_fields_validation_success(self):
        """
        Test valid values for percentage fields.
        """
        settings = self.settings
        settings.cancellation_full_payment_partial_refund_percentage = Decimal('25.50')
        settings.cancellation_full_payment_minimal_refund_percentage = Decimal('5.00')
        settings.cancellation_deposit_partial_refund_percentage = Decimal('99.99')
        settings.cancellation_deposit_minimal_refund_percentage = Decimal('0.00')
        settings.full_clean() # Should not raise ValidationError

    def test_percentage_fields_validation_failure_too_high(self):
        """
        Test that percentage fields raise ValidationError if over 100.00.
        """
        settings = self.settings
        settings.cancellation_full_payment_partial_refund_percentage = Decimal('100.01')
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('cancellation_full_payment_partial_refund_percentage', cm.exception.message_dict)

    def test_percentage_fields_validation_failure_too_low(self):
        """
        Test that percentage fields raise ValidationError if under 0.00.
        """
        settings = self.settings
        settings.cancellation_full_payment_minimal_refund_percentage = Decimal('-0.01')
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('cancellation_full_payment_minimal_refund_percentage', cm.exception.message_dict)

    def test_stripe_fee_percentage_validation_success(self):
        """
        Test valid values for Stripe fee percentage fields.
        """
        settings = self.settings
        settings.stripe_fee_percentage_domestic = Decimal('0.0500') # 5%
        settings.stripe_fee_percentage_international = Decimal('0.0999') # 9.99%
        settings.full_clean() # Should not raise ValidationError

    def test_stripe_fee_percentage_validation_failure_too_high(self):
        """
        Test that Stripe fee percentage fields raise ValidationError if over 0.10 (10%).
        """
        settings = self.settings
        settings.stripe_fee_percentage_domestic = Decimal('0.1001')
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('stripe_fee_percentage_domestic', cm.exception.message_dict)

    def test_days_thresholds_validation_success(self):
        """
        Test valid ordering for days thresholds.
        """
        settings = self.settings
        # Full payment days
        settings.cancellation_full_payment_full_refund_days = 10
        settings.cancellation_full_payment_partial_refund_days = 5
        settings.cancellation_full_payment_minimal_refund_days = 1
        # Deposit days
        settings.cancellation_deposit_full_refund_days = 8
        settings.cancellation_deposit_partial_refund_days = 4
        settings.cancellation_deposit_minimal_refund_days = 0
        settings.full_clean() # Should not raise ValidationError

    def test_days_thresholds_validation_failure_full_payment_order(self):
        """
        Test invalid ordering for full payment days thresholds.
        """
        settings = self.settings
        settings.cancellation_full_payment_full_refund_days = 2
        settings.cancellation_full_payment_partial_refund_days = 5 # Invalid: full < partial
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('cancellation_full_payment_full_refund_days', cm.exception.message_dict)

        settings = self.settings
        settings.cancellation_full_payment_partial_refund_days = 0
        settings.cancellation_full_payment_minimal_refund_days = 1 # Invalid: partial < minimal
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('cancellation_full_payment_partial_refund_days', cm.exception.message_dict)

    def test_days_thresholds_validation_failure_deposit_order(self):
        """
        Test invalid ordering for deposit days thresholds.
        """
        settings = self.settings
        settings.cancellation_deposit_full_refund_days = 2
        settings.cancellation_deposit_partial_refund_days = 5 # Invalid: full < partial
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('cancellation_deposit_full_refund_days', cm.exception.message_dict)

        settings = self.settings
        settings.cancellation_deposit_partial_refund_days = 0
        settings.cancellation_deposit_minimal_refund_days = 1 # Invalid: partial < minimal
        with self.assertRaises(ValidationError) as cm:
            settings.full_clean()
        self.assertIn('cancellation_deposit_partial_refund_days', cm.exception.message_dict)
