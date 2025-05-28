# payments/tests/test_payment_model.py

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import uuid

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_payment,
    create_temp_hire_booking,
    create_hire_booking,
    create_driver_profile,
    create_motorcycle # Needed for creating bookings
)
# Import the Payment model directly for specific tests if needed
from payments.models import Payment
from hire.models import TempHireBooking, HireBooking, DriverProfile


class PaymentModelTest(TestCase):
    """
    Unit tests for the Payment model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create some related objects that payments can link to.
        """
        cls.motorcycle = create_motorcycle()
        cls.driver_profile = create_driver_profile(name="Test Driver")
        cls.temp_booking = create_temp_hire_booking(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            total_hire_price=Decimal('200.00'),
            grand_total=Decimal('250.00')
        )
        cls.hire_booking = create_hire_booking(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            total_hire_price=Decimal('300.00'),
            grand_total=Decimal('350.00')
        )
        cls.stripe_pi_id_1 = "pi_test_12345"
        cls.stripe_pi_id_2 = "pi_test_67890"

    def test_create_basic_payment(self):
        """
        Test that a basic Payment instance can be created with required fields.
        """
        payment = create_payment(
            amount=Decimal('150.00'),
            currency='USD',
            status='succeeded',
            stripe_payment_intent_id=self.stripe_pi_id_1
        )
        self.assertIsNotNone(payment.pk)
        self.assertEqual(payment.amount, Decimal('150.00'))
        self.assertEqual(payment.currency, 'USD')
        self.assertEqual(payment.status, 'succeeded')
        self.assertEqual(payment.stripe_payment_intent_id, self.stripe_pi_id_1)
        self.assertIsNone(payment.temp_hire_booking)
        self.assertIsNone(payment.hire_booking)
        self.assertIsNone(payment.driver_profile)
        self.assertIsNotNone(payment.created_at)
        self.assertIsNotNone(payment.updated_at)
        self.assertEqual(payment.metadata, {}) # Check default for JSONField

    def test_str_method(self):
        """
        Test the __str__ method of Payment.
        """
        payment = create_payment(
            amount=Decimal('250.00'),
            currency='AUD',
            status='requires_action',
            temp_hire_booking=self.temp_booking,
            hire_booking=self.hire_booking,
            stripe_payment_intent_id=self.stripe_pi_id_2
        )
        expected_str = (
            f"Payment {payment.id} (Temp: {self.temp_booking.id}, Hire: {self.hire_booking.booking_reference}) "
            f"- Amount: {payment.amount} {payment.currency} - Status: {payment.status}"
        )
        self.assertEqual(str(payment), expected_str)

        # Test with only temp_hire_booking
        payment_temp_only = create_payment(
            amount=Decimal('50.00'),
            temp_hire_booking=self.temp_booking,
            status='pending'
        )
        expected_str_temp_only = (
            f"Payment {payment_temp_only.id} (Temp: {self.temp_booking.id}, Hire: N/A) "
            f"- Amount: {payment_temp_only.amount} {payment_temp_only.currency} - Status: {payment_temp_only.status}"
        )
        self.assertEqual(str(payment_temp_only), expected_str_temp_only)

        # Test with only hire_booking
        payment_hire_only = create_payment(
            amount=Decimal('75.00'),
            hire_booking=self.hire_booking,
            status='succeeded'
        )
        expected_str_hire_only = (
            f"Payment {payment_hire_only.id} (Temp: N/A, Hire: {self.hire_booking.booking_reference}) "
            f"- Amount: {payment_hire_only.amount} {payment_hire_only.currency} - Status: {payment_hire_only.status}"
        )
        self.assertEqual(str(payment_hire_only), expected_str_hire_only)

        # Test with no bookings
        payment_no_booking = create_payment(amount=Decimal('10.00'))
        expected_str_no_booking = (
            f"Payment {payment_no_booking.id} (Temp: N/A, Hire: N/A) "
            f"- Amount: {payment_no_booking.amount} {payment_no_booking.currency} - Status: {payment_no_booking.status}"
        )
        self.assertEqual(str(payment_no_booking), expected_str_no_booking)


    def test_temp_hire_booking_relationship(self):
        """
        Test the OneToOneField relationship with TempHireBooking.
        """
        payment = create_payment(
            amount=Decimal('100.00'),
            temp_hire_booking=self.temp_booking
        )
        self.assertEqual(payment.temp_hire_booking, self.temp_booking)
        self.assertEqual(self.temp_booking.payment, payment) # Check related_name

        # Ensure only one payment can be linked to a temp booking
        with self.assertRaises(IntegrityError):
            create_payment(
                amount=Decimal('50.00'),
                temp_hire_booking=self.temp_booking # This should fail as temp_booking already has a payment
            )

    def test_hire_booking_relationship(self):
        """
        Test the ForeignKey relationship with HireBooking.
        """
        payment1 = create_payment(
            amount=Decimal('200.00'),
            hire_booking=self.hire_booking
        )
        payment2 = create_payment(
            amount=Decimal('50.00'),
            hire_booking=self.hire_booking,
            stripe_payment_intent_id="pi_another_id" # Needs unique PI ID
        )
        self.assertEqual(payment1.hire_booking, self.hire_booking)
        self.assertEqual(payment2.hire_booking, self.hire_booking)
        self.assertIn(payment1, self.hire_booking.payments.all())
        self.assertIn(payment2, self.hire_booking.payments.all())
        self.assertEqual(self.hire_booking.payments.count(), 2)

    def test_driver_profile_relationship(self):
        """
        Test the ForeignKey relationship with DriverProfile.
        """
        payment1 = create_payment(
            amount=Decimal('120.00'),
            driver_profile=self.driver_profile
        )
        payment2 = create_payment(
            amount=Decimal('80.00'),
            driver_profile=self.driver_profile,
            stripe_payment_intent_id="pi_yet_another_id" # Needs unique PI ID
        )
        self.assertEqual(payment1.driver_profile, self.driver_profile)
        self.assertEqual(payment2.driver_profile, self.driver_profile)
        self.assertIn(payment1, self.driver_profile.payments.all())
        self.assertIn(payment2, self.driver_profile.payments.all())
        self.assertEqual(self.driver_profile.payments.count(), 2)

    def test_stripe_payment_intent_id_uniqueness(self):
        """
        Test that stripe_payment_intent_id is unique.
        """
        create_payment(
            amount=Decimal('10.00'),
            stripe_payment_intent_id="pi_unique_id_1"
        )
        with self.assertRaises(IntegrityError):
            create_payment(
                amount=Decimal('20.00'),
                stripe_payment_intent_id="pi_unique_id_1" # Duplicate ID
            )

    def test_default_values(self):
        """
        Test that default values for currency and status are applied.
        """
        payment = create_payment(amount=Decimal('50.00'))
        self.assertEqual(payment.currency, 'AUD')
        self.assertEqual(payment.status, 'pending') # Factory default is 'pending'

        # Check model's default for status if not set by factory
        # To do this, we need to bypass the factory's default 'pending'
        payment_model_default = Payment.objects.create(amount=Decimal('75.00'))
        self.assertEqual(payment_model_default.status, 'requires_payment_method')
        self.assertEqual(payment_model_default.currency, 'AUD')

    def test_amount_decimal_field(self):
        """
        Test DecimalField properties for amount.
        """
        payment = create_payment(amount=Decimal('1234567.89'))
        self.assertEqual(payment.amount, Decimal('1234567.89'))

        # Test with more than 2 decimal places (should be rounded)
        payment_rounded = create_payment(amount=Decimal('100.123'))
        self.assertEqual(payment_rounded.amount, Decimal('100.12'))

        # Test max_digits (99,999,999.99 should pass)
        large_amount = Decimal('99999999.99')
        payment_large = create_payment(amount=large_amount)
        self.assertEqual(payment_large.amount, large_amount)

        # Test exceeding max_digits (this would typically raise a validation error
        # on save if using forms, but direct model creation might truncate or raise DB error)
        # For simplicity, we'll test a valid case here.
        # A full test for max_digits/decimal_places would involve model clean() or form validation.

    def test_on_delete_temp_hire_booking_set_null(self):
        """
        Test that temp_hire_booking is set to NULL when TempHireBooking is deleted.
        """
        payment = create_payment(
            amount=Decimal('100.00'),
            temp_hire_booking=self.temp_booking
        )
        temp_booking_id = self.temp_booking.id
        self.temp_booking.delete()
        payment.refresh_from_db()
        self.assertIsNone(payment.temp_hire_booking)
        self.assertFalse(TempHireBooking.objects.filter(id=temp_booking_id).exists())
        self.assertTrue(Payment.objects.filter(id=payment.id).exists()) # Payment still exists

    def test_on_delete_hire_booking_set_null(self):
        """
        Test that hire_booking is set to NULL when HireBooking is deleted.
        """
        payment = create_payment(
            amount=Decimal('200.00'),
            hire_booking=self.hire_booking,
            stripe_payment_intent_id="pi_delete_test_hire"
        )
        hire_booking_ref = self.hire_booking.booking_reference
        self.hire_booking.delete()
        payment.refresh_from_db()
        self.assertIsNone(payment.hire_booking)
        self.assertFalse(HireBooking.objects.filter(booking_reference=hire_booking_ref).exists())
        self.assertTrue(Payment.objects.filter(id=payment.id).exists()) # Payment still exists

    def test_on_delete_driver_profile_set_null(self):
        """
        Test that driver_profile is set to NULL when DriverProfile is deleted.
        """
        payment = create_payment(
            amount=Decimal('50.00'),
            driver_profile=self.driver_profile,
            stripe_payment_intent_id="pi_delete_test_driver"
        )
        driver_profile_id = self.driver_profile.id
        self.driver_profile.delete()
        payment.refresh_from_db()
        self.assertIsNone(payment.driver_profile)
        self.assertFalse(DriverProfile.objects.filter(id=driver_profile_id).exists())
        self.assertTrue(Payment.objects.filter(id=payment.id).exists()) # Payment still exists

    def test_ordering_by_created_at(self):
        """
        Test that payments are ordered by created_at in descending order.
        """
        import time
        payment1 = create_payment(amount=Decimal('10.00'), stripe_payment_intent_id="pi_order_1")
        time.sleep(0.01) # Ensure different creation times
        payment2 = create_payment(amount=Decimal('20.00'), stripe_payment_intent_id="pi_order_2")
        time.sleep(0.01)
        payment3 = create_payment(amount=Decimal('30.00'), stripe_payment_intent_id="pi_order_3")

        # Fetch all payments and check their order
        all_payments = Payment.objects.all()
        self.assertEqual(list(all_payments), [payment3, payment2, payment1])

    def test_metadata_json_field(self):
        """
        Test the metadata JSONField.
        """
        metadata_data = {
            "customer_email": "test@example.com",
            "booking_type": "rental",
            "items": ["motorcycle", "helmet"]
        }
        payment = create_payment(
            amount=Decimal('300.00'),
            metadata=metadata_data,
            stripe_payment_intent_id="pi_metadata_test"
        )
        self.assertEqual(payment.metadata, metadata_data)

        # Test updating metadata
        payment.metadata['new_key'] = 'new_value'
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.metadata['new_key'], 'new_value')

        # Test with empty metadata (default case)
        payment_empty_meta = create_payment(
            amount=Decimal('50.00'),
            stripe_payment_intent_id="pi_empty_meta"
        )
        self.assertEqual(payment_empty_meta.metadata, {})

    def test_stripe_payment_method_id(self):
        """
        Test that stripe_payment_method_id can be set.
        """
        payment = create_payment(
            amount=Decimal('75.00'),
            stripe_payment_method_id="pm_card_visa",
            stripe_payment_intent_id="pi_method_id_test"
        )
        self.assertEqual(payment.stripe_payment_method_id, "pm_card_visa")
        self.assertIsNone(payment.description) # Check default null

    def test_description_field(self):
        """
        Test the description TextField.
        """
        description_text = "Payment for 3-day motorcycle rental for customer John Doe."
        payment = create_payment(
            amount=Decimal('400.00'),
            description=description_text,
            stripe_payment_intent_id="pi_description_test"
        )
        self.assertEqual(payment.description, description_text)

        # Test with blank description
        payment_blank_desc = create_payment(
            amount=Decimal('10.00'),
            description="",
            stripe_payment_intent_id="pi_blank_desc"
        )
        self.assertEqual(payment_blank_desc.description, "")

        # Test with null description (default)
        payment_null_desc = create_payment(
            amount=Decimal('20.00'),
            stripe_payment_intent_id="pi_null_desc"
        )
        self.assertIsNone(payment_null_desc.description)

