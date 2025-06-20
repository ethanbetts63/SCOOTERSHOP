# payments/tests/test_payment_model.py

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
import uuid
import time

# Import model factories from the new file
from ..test_helpers.model_factories import (
    PaymentFactory,
    TempHireBookingFactory,
    HireBookingFactory,
    DriverProfileFactory,
    MotorcycleFactory, # Now importing the real MotorcycleFactory
    MotorcycleConditionFactory, # Also import MotorcycleConditionFactory if you plan to use it
    TempServiceBookingFactory, # Import for service booking related tests
    ServiceBookingFactory, # Import for service booking related tests
    ServiceProfileFactory, # Import for service booking related tests
)

# Import the Payment model directly for specific tests if needed
from payments.models import Payment
from hire.models import TempHireBooking, HireBooking, DriverProfile
from service.models import TempServiceBooking, ServiceBooking, ServiceProfile


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
        # Ensure 'hire' condition exists for motorcycle creation
        MotorcycleConditionFactory.create(name='hire', display_name='Hire')
        # Use the new factories
        cls.motorcycle = MotorcycleFactory.create()
        cls.driver_profile = DriverProfileFactory.create(name="Test Driver")
        cls.temp_booking = TempHireBookingFactory.create(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            total_hire_price=Decimal('200.00'),
            grand_total=Decimal('250.00')
        )
        cls.hire_booking = HireBookingFactory.create(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            total_hire_price=Decimal('300.00'),
            grand_total=Decimal('350.00')
        )
        cls.temp_service_booking = TempServiceBookingFactory.create()
        cls.service_profile = ServiceProfileFactory.create(name="Service Customer Name")
        cls.service_booking = ServiceBookingFactory.create(
            service_profile=cls.service_profile # Link to the created service profile
        )


        cls.stripe_pi_id_1 = "pi_test_12345"
        cls.stripe_pi_id_2 = "pi_test_67890"

    def test_create_basic_payment(self):
        """
        Test that a basic Payment instance can be created with required fields.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
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
        # The factory's metadata is now set to default to an empty dict for this test case
        self.assertEqual(payment.metadata, {}) # Check default for JSONField

    def test_temp_hire_booking_relationship(self):
        """
        Test the OneToOneField relationship with TempHireBooking.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('100.00'),
            temp_hire_booking=self.temp_booking
        )
        self.assertEqual(payment.temp_hire_booking, self.temp_booking)
        self.assertEqual(self.temp_booking.payment, payment) # Check related_name

        # Ensure only one payment can be linked to a temp booking
        with self.assertRaises(IntegrityError):
            PaymentFactory.create(
                amount=Decimal('50.00'),
                temp_hire_booking=self.temp_booking # This should fail as temp_booking already has a payment
            )

    def test_hire_booking_relationship(self):
        """
        Test the ForeignKey relationship with HireBooking.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment1 = PaymentFactory.create(
            amount=Decimal('200.00'),
            hire_booking=self.hire_booking
        )
        payment2 = PaymentFactory.create(
            amount=Decimal('50.00'),
            hire_booking=self.hire_booking,
            # stripe_payment_intent_id is automatically generated by factory now
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
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment1 = PaymentFactory.create(
            amount=Decimal('120.00'),
            driver_profile=self.driver_profile
        )
        payment2 = PaymentFactory.create(
            amount=Decimal('80.00'),
            driver_profile=self.driver_profile,
            # stripe_payment_intent_id is automatically generated by factory now
        )
        self.assertEqual(payment1.driver_profile, self.driver_profile)
        self.assertEqual(payment2.driver_profile, self.driver_profile)
        self.assertIn(payment1, self.driver_profile.payments.all())
        self.assertIn(payment2, self.driver_profile.payments.all())
        self.assertEqual(self.driver_profile.payments.count(), 2)

    def test_temp_service_booking_relationship(self):
        """
        Test the OneToOneField relationship with TempServiceBooking.
        """
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('100.00'),
            temp_service_booking=self.temp_service_booking
        )
        self.assertEqual(payment.temp_service_booking, self.temp_service_booking)
        self.assertEqual(self.temp_service_booking.payment_for_temp_service, payment)

        with self.assertRaises(IntegrityError):
            PaymentFactory.create(
                amount=Decimal('50.00'),
                temp_service_booking=self.temp_service_booking
            )

    def test_service_booking_relationship(self):
        """
        Test the ForeignKey relationship with ServiceBooking.
        """
        Payment.objects.all().delete()
        payment1 = PaymentFactory.create(
            amount=Decimal('200.00'),
            service_booking=self.service_booking
        )
        payment2 = PaymentFactory.create(
            amount=Decimal('50.00'),
            service_booking=self.service_booking
        )
        self.assertEqual(payment1.service_booking, self.service_booking)
        self.assertEqual(payment2.service_booking, self.service_booking)
        self.assertIn(payment1, self.service_booking.payments_for_service.all())
        self.assertIn(payment2, self.service_booking.payments_for_service.all())
        self.assertEqual(self.service_booking.payments_for_service.count(), 2)

    def test_service_customer_profile_relationship(self):
        """
        Test the ForeignKey relationship with ServiceProfile.
        """
        Payment.objects.all().delete()
        payment1 = PaymentFactory.create(
            amount=Decimal('120.00'),
            service_customer_profile=self.service_profile
        )
        payment2 = PaymentFactory.create(
            amount=Decimal('80.00'),
            service_customer_profile=self.service_profile
        )
        self.assertEqual(payment1.service_customer_profile, self.service_profile)
        self.assertEqual(payment2.service_customer_profile, self.service_profile)
        self.assertIn(payment1, self.service_profile.payments_by_service_customer.all())
        self.assertIn(payment2, self.service_profile.payments_by_service_customer.all())
        self.assertEqual(self.service_profile.payments_by_service_customer.count(), 2)


    def test_stripe_payment_intent_id_uniqueness(self):
        """
        Test that stripe_payment_intent_id is unique.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        # The factory automatically generates unique IDs, so this should pass
        PaymentFactory.create(
            amount=Decimal('10.00')
        )
        with self.assertRaises(IntegrityError):
            # To test uniqueness, we need to explicitly pass a duplicate
            # as the factory ensures uniqueness by default.
            duplicate_pi_id = "pi_manual_duplicate_id"
            PaymentFactory.create(amount=Decimal('10.00'), stripe_payment_intent_id=duplicate_pi_id)
            PaymentFactory.create(amount=Decimal('20.00'), stripe_payment_intent_id=duplicate_pi_id)


    def test_default_values(self):
        """
        Test that default values for currency and status are applied.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(amount=Decimal('50.00'))
        self.assertEqual(payment.currency, 'AUD')
        # The factory's default for status is random, so we need to test the model's actual default
        # or explicitly set it in the factory to match a specific expected default.
        # Given the factory's random element for status, we test the model's default directly.

        # Check model's default for status if not set by factory
        payment_model_default = Payment.objects.create(amount=Decimal('75.00'), stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:24]}")
        self.assertEqual(payment_model_default.status, 'requires_payment_method')
        self.assertEqual(payment_model_default.currency, 'AUD')


    def test_amount_decimal_field(self):
        """
        Test DecimalField properties for amount.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(amount=Decimal('1234567.89'))
        self.assertEqual(payment.amount, Decimal('1234567.89'))

        # Test with more than 2 decimal places (should be rounded)
        payment_rounded = PaymentFactory.create(amount=Decimal('100.123'))
        payment_rounded.refresh_from_db() # Added to refresh from DB and ensure rounding
        self.assertEqual(payment_rounded.amount, Decimal('100.12'))

        # Test max_digits (99,999,999.99 should pass)
        large_amount = Decimal('99999999.99')
        payment_large = PaymentFactory.create(amount=large_amount)
        self.assertEqual(payment_large.amount, large_amount)

        # Test exceeding max_digits (this would typically raise a validation error
        # on save if using forms, but direct model creation might truncate or raise DB error)
        # For simplicity, we'll test a valid case here.
        # A full test for max_digits/decimal_places would involve model clean() or form validation.

    def test_on_delete_temp_hire_booking_set_null(self):
        """
        Test that temp_hire_booking is set to NULL when TempHireBooking is deleted.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
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
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('200.00'),
            hire_booking=self.hire_booking,
            # stripe_payment_intent_id is automatically generated by factory now
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
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('50.00'),
            driver_profile=self.driver_profile,
            # stripe_payment_intent_id is automatically generated by factory now
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
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        # The factory now auto-generates unique stripe_payment_intent_id,
        # so we don't need to pass it explicitly unless testing specific IDs.
        payment1 = PaymentFactory.create(amount=Decimal('10.00'))
        time.sleep(0.01) # Ensure different creation times
        payment2 = PaymentFactory.create(amount=Decimal('20.00'))
        time.sleep(0.01)
        payment3 = PaymentFactory.create(amount=Decimal('30.00'))

        # Fetch all payments and check their order
        all_payments = Payment.objects.all()
        self.assertEqual(list(all_payments), [payment3, payment2, payment1])
        # Also ensure no extra payments are created by other setup logic
        self.assertEqual(Payment.objects.count(), 3)


    def test_metadata_json_field(self):
        """
        Test the metadata JSONField.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        metadata_data = {
            "customer_email": "test@example.com",
            "booking_type": "rental",
            "items": ["motorcycle", "helmet"]
        }
        payment = PaymentFactory.create(
            amount=Decimal('300.00'),
            metadata=metadata_data,
        )
        self.assertEqual(payment.metadata, metadata_data)

        # Test updating metadata
        payment.metadata['new_key'] = 'new_value'
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.metadata['new_key'], 'new_value')

        # Test with empty metadata (default case)
        # Factory's default for metadata is a dictionary, so we need to override it to test empty
        payment_empty_meta = PaymentFactory.create(
            amount=Decimal('50.00'),
            metadata={},
        )
        self.assertEqual(payment_empty_meta.metadata, {})

    def test_stripe_payment_method_id(self):
        """
        Test that stripe_payment_method_id can be set.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        payment = PaymentFactory.create(
            amount=Decimal('75.00'),
            stripe_payment_method_id="pm_card_visa",
        )
        self.assertEqual(payment.stripe_payment_method_id, "pm_card_visa")
        # Factory's default for description is a sentence, so we test the model's actual default
        payment_model_default = Payment.objects.create(
            amount=Decimal('75.00'),
            stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:24]}"
        )
        self.assertIsNone(payment_model_default.description) # Check default null

    def test_description_field(self):
        """
        Test the description TextField.
        """
        # Clear Payments to ensure test isolation for this specific method
        Payment.objects.all().delete()
        description_text = "Payment for 3-day motorcycle rental for customer John Doe."
        payment = PaymentFactory.create(
            amount=Decimal('400.00'),
            description=description_text,
        )
        self.assertEqual(payment.description, description_text)

        # Test with blank description
        payment_blank_desc = PaymentFactory.create(
            amount=Decimal('10.00'),
            description="",
        )
        self.assertEqual(payment_blank_desc.description, "")

        # Test with null description (default)
        # Factory's default for description is a sentence, so we test the model's actual default
        payment_null_desc = Payment.objects.create(
            amount=Decimal('20.00'),
            stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:24]}"
        )
        self.assertIsNone(payment_null_desc.description)
