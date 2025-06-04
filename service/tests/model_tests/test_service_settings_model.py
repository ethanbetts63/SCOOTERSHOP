from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

# Import the ServiceSettings model
from service.models import ServiceSettings

# Import the ServiceSettingsFactory from your factories file
# Adjust the import path if your model_factories.py is in a different location
from ..test_helpers.model_factories import ServiceSettingsFactory

class ServiceSettingsModelTest(TestCase):
    """
    Tests for the ServiceSettings model, including its singleton pattern
    and field validations.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up the single instance of ServiceSettings used by all test methods.
        The ServiceSettingsFactory ensures only one instance exists (pk=1).
        """
        cls.settings = ServiceSettingsFactory()

    def test_singleton_creation(self):
        """
        Test that only one instance of ServiceSettings can be created.
        The factory's django_get_or_create and the model's save method
        should ensure this.
        """
        # Verify the instance created in setUpTestData exists
        self.assertIsNotNone(self.settings)
        self.assertEqual(ServiceSettings.objects.count(), 1)

        # Attempt to create another instance directly, it should raise ValidationError
        with self.assertRaisesMessage(ValidationError, "Only one instance of ServiceSettings can be created. Please edit the existing one."):
            # We need to explicitly set pk=None or omit it to simulate a new object creation
            # The save method's logic checks `if not self.pk`
            ServiceSettings(pk=None, enable_service_booking=False).save()

        # Verify that still only one instance exists in the database
        self.assertEqual(ServiceSettings.objects.count(), 1)

        # Test that calling the factory again returns the same instance
        retrieved_settings = ServiceSettingsFactory()
        self.assertEqual(self.settings.pk, retrieved_settings.pk)
        self.assertEqual(self.settings.enable_service_booking, retrieved_settings.enable_service_booking)


    def test_field_defaults_and_types(self):
        """
        Test the default values and data types of various fields.
        """
        settings = self.settings

        # Boolean fields
        self.assertIsInstance(settings.enable_service_booking, bool)
        self.assertTrue(settings.enable_service_booking)
        self.assertIsInstance(settings.allow_anonymous_bookings, bool)
        self.assertTrue(settings.allow_anonymous_bookings)
        self.assertIsInstance(settings.enable_deposit, bool)
        self.assertFalse(settings.enable_deposit)
        self.assertIsInstance(settings.refund_deducts_stripe_fee_policy, bool)
        self.assertTrue(settings.refund_deducts_stripe_fee_policy)

        # Integer fields
        self.assertIsInstance(settings.booking_advance_notice, int)
        self.assertEqual(settings.booking_advance_notice, 1)
        self.assertIsInstance(settings.max_visible_slots_per_day, int)
        self.assertEqual(settings.max_visible_slots_per_day, 6)
        self.assertIsInstance(settings.cancel_full_payment_max_refund_days, int)
        self.assertEqual(settings.cancel_full_payment_max_refund_days, 7)

        # CharField fields
        self.assertIsInstance(settings.booking_open_days, str)
        self.assertEqual(settings.booking_open_days, "Mon,Tue,Wed,Thu,Fri")
        self.assertEqual(settings._meta.get_field('booking_open_days').max_length, 255)
        self.assertIsInstance(settings.currency_code, str)
        self.assertEqual(settings.currency_code, 'AUD')
        self.assertIsInstance(settings.currency_symbol, str)
        self.assertEqual(settings.currency_symbol, '$')

        # TextField
        self.assertIsInstance(settings.other_brand_policy_text, str)
        self.assertEqual(settings._meta.get_field('other_brand_policy_text').blank, True)

        # DecimalField fields
        self.assertIsInstance(settings.deposit_flat_fee_amount, Decimal)
        self.assertEqual(settings.deposit_flat_fee_amount, Decimal('0.00'))
        self.assertEqual(settings._meta.get_field('deposit_flat_fee_amount').max_digits, 10)
        self.assertEqual(settings._meta.get_field('deposit_flat_fee_amount').decimal_places, 2)

        self.assertIsInstance(settings.deposit_percentage, Decimal)
        self.assertEqual(settings.deposit_percentage, Decimal('0.00'))
        self.assertEqual(settings._meta.get_field('deposit_percentage').max_digits, 5)
        self.assertEqual(settings._meta.get_field('deposit_percentage').decimal_places, 2)

        self.assertIsInstance(settings.stripe_fee_percentage, Decimal)
        self.assertEqual(settings.stripe_fee_percentage, Decimal('0.0290'))
        self.assertEqual(settings._meta.get_field('stripe_fee_percentage').max_digits, 5)
        self.assertEqual(settings._meta.get_field('stripe_fee_percentage').decimal_places, 4)

        self.assertIsInstance(settings.stripe_fee_fixed, Decimal)
        self.assertEqual(settings.stripe_fee_fixed, Decimal('0.30'))
        self.assertEqual(settings._meta.get_field('stripe_fee_fixed').max_digits, 5)
        self.assertEqual(settings._meta.get_field('stripe_fee_fixed').decimal_places, 2)

        # Choices field
        self.assertEqual(settings.deposit_calc_method, 'FLAT_FEE')
        self.assertIn(('FLAT_FEE', 'Flat Fee'), settings.DEPOSIT_CALC_CHOICES)
        self.assertIn(('PERCENTAGE', 'Percentage of Booking Total'), settings.DEPOSIT_CALC_CHOICES)


    def test_clean_method_percentage_validation(self):
        """
        Test the clean method's validation for percentage fields (0.00 to 1.00).
        """
        settings = self.settings

        # Test valid percentages
        settings.deposit_percentage = Decimal('0.50')
        settings.cancel_full_payment_max_refund_percentage = Decimal('1.00')
        settings.cancel_deposit_min_refund_percentage = Decimal('0.00')
        settings.full_clean() # Should not raise error

        # Test invalid percentages (greater than 1.00)
        settings.deposit_percentage = Decimal('1.01')
        with self.assertRaisesMessage(ValidationError, "Ensure deposit percentage is between 0.00 (0%) and 1.00 (100%)."):
            settings.full_clean()
        settings.deposit_percentage = Decimal('0.50') # Reset

        settings.cancel_full_payment_partial_refund_percentage = Decimal('1.50')
        with self.assertRaisesMessage(ValidationError, "Ensure cancel full payment partial refund percentage is between 0.00 (0%) and 1.00 (100%)."):
            settings.full_clean()
        settings.cancel_full_payment_partial_refund_percentage = Decimal('0.50') # Reset

        # Test invalid percentages (less than 0.00)
        settings.cancel_deposit_max_refund_percentage = Decimal('-0.10')
        with self.assertRaisesMessage(ValidationError, "Ensure cancel deposit max refund percentage is between 0.00 (0%) and 1.00 (100%)."):
            settings.full_clean()
        settings.cancel_deposit_max_refund_percentage = Decimal('1.00') # Reset

    def test_clean_method_stripe_fee_percentage_validation(self):
        """
        Test the clean method's specific validation for stripe_fee_percentage (0.00 to 0.10).
        """
        settings = self.settings

        # Test valid stripe_fee_percentage
        settings.stripe_fee_percentage = Decimal('0.05')
        settings.full_clean() # Should not raise error

        settings.stripe_fee_percentage = Decimal('0.00')
        settings.full_clean() # Should not raise error

        settings.stripe_fee_percentage = Decimal('0.10')
        settings.full_clean() # Should not raise error

        # Test invalid stripe_fee_percentage (greater than 0.10)
        settings.stripe_fee_percentage = Decimal('0.11')
        with self.assertRaisesMessage(ValidationError, "Ensure stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."):
            settings.full_clean()
        settings.stripe_fee_percentage = Decimal('0.0290') # Reset

        # Test invalid stripe_fee_percentage (less than 0.00)
        settings.stripe_fee_percentage = Decimal('-0.01')
        with self.assertRaisesMessage(ValidationError, "Ensure stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."):
            settings.full_clean()
        settings.stripe_fee_percentage = Decimal('0.0290') # Reset


    def test_str_method(self):
        """
        Test the __str__ method of the ServiceSettings model.
        """
        settings = self.settings
        self.assertEqual(str(settings), "Service Booking Settings")

    def test_meta_options(self):
        """
        Test the Meta options of the ServiceSettings model.
        """
        self.assertEqual(ServiceSettings._meta.verbose_name, "Service Settings")
        self.assertEqual(ServiceSettings._meta.verbose_name_plural, "Service Settings")
