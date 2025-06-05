from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError # Import IntegrityError for specific checks
from decimal import Decimal
import datetime
import uuid

# Import the ServiceBooking model
from service.models import ServiceBooking

# Import the ServiceBookingFactory from your factories file
# Adjust the import path if your model_factories.py is in a different location
from ..test_helpers.model_factories import ServiceBookingFactory, ServiceTypeFactory, ServiceProfileFactory, CustomerMotorcycleFactory, PaymentFactory

class ServiceBookingModelTest(TestCase):
    """
    Tests for the ServiceBooking model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.service_booking = ServiceBookingFactory()

    def test_service_booking_creation(self):
        """
        Test that a ServiceBooking instance can be created using the factory.
        """
        self.assertIsNotNone(self.service_booking)
        self.assertIsInstance(self.service_booking, ServiceBooking)
        self.assertEqual(ServiceBooking.objects.count(), 1)

    def test_booking_reference_generation_on_save(self):
        """
        Test that booking_reference is automatically generated if not provided.
        """
        # Create a booking without providing a booking_reference
        booking = ServiceBookingFactory(booking_reference=None)
        
        # Check that a reference was generated and it's not empty
        self.assertIsNotNone(booking.booking_reference)
        self.assertNotEqual(booking.booking_reference, "")
        self.assertTrue(booking.booking_reference.startswith("SERVICE-"))
        self.assertEqual(len(booking.booking_reference), 8 + len("SERVICE-")) # SERVICE-XXXXXXXX

        # Test saving an existing booking (should not change the reference)
        old_reference = booking.booking_reference
        booking.customer_notes = "Updated notes"
        booking.save()
        self.assertEqual(booking.booking_reference, old_reference)

    def test_str_method(self):
        """
        Test the __str__ method of the ServiceBooking model.
        """
        expected_str = f"Booking {self.service_booking.booking_reference} for {self.service_booking.service_profile.name} on {self.service_booking.dropoff_date}"
        self.assertEqual(str(self.service_booking), expected_str)

    def test_field_attributes(self):
        """
        Test the attributes of various fields in the ServiceBooking model.
        """
        booking = self.service_booking

        # booking_reference
        field = booking._meta.get_field('booking_reference')
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.unique)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # service_type
        field = booking._meta.get_field('service_type')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceType')
        # FIX: Access on_delete through remote_field
        self.assertEqual(field.remote_field.on_delete, models.PROTECT)

        # service_profile
        field = booking._meta.get_field('service_profile')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceProfile')
        # FIX: Access on_delete through remote_field
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

        # customer_motorcycle
        field = booking._meta.get_field('customer_motorcycle')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'CustomerMotorcycle')
        # FIX: Access on_delete through remote_field
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # payment_option
        field = booking._meta.get_field('payment_option')
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertGreater(len(field.choices), 0)

        # payment
        field = booking._meta.get_field('payment')
        self.assertIsInstance(field, models.OneToOneField)
        self.assertEqual(field.related_model.__name__, 'Payment')
        # FIX: Access on_delete through remote_field
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # calculated_total, calculated_deposit_amount, amount_paid
        for field_name in ['calculated_total', 'calculated_deposit_amount', 'amount_paid']:
            field = booking._meta.get_field(field_name)
            self.assertIsInstance(field, models.DecimalField)
            self.assertEqual(field.decimal_places, 2)
            self.assertIsInstance(getattr(booking, field_name), Decimal)
            self.assertGreaterEqual(getattr(booking, field_name), Decimal('0.00'))

        self.assertEqual(booking._meta.get_field('calculated_total').max_digits, 10)
        self.assertEqual(booking._meta.get_field('calculated_deposit_amount').max_digits, 8)
        self.assertEqual(booking._meta.get_field('amount_paid').max_digits, 10)

        # payment_status
        field = booking._meta.get_field('payment_status')
        self.assertEqual(field.max_length, 20)
        self.assertEqual(field.default, 'unpaid')
        self.assertGreater(len(field.choices), 0)

        # payment_method
        field = booking._meta.get_field('payment_method')
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertGreater(len(field.choices), 0)

        # currency
        field = booking._meta.get_field('currency')
        self.assertEqual(field.max_length, 3)
        self.assertEqual(field.default, 'AUD')

        # stripe_payment_intent_id
        field = booking._meta.get_field('stripe_payment_intent_id')
        self.assertEqual(field.max_length, 100)
        self.assertTrue(field.unique)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # dropoff_date
        field = booking._meta.get_field('dropoff_date')
        self.assertIsInstance(field, models.DateField)
        self.assertIsInstance(booking.dropoff_date, datetime.date)

        # dropoff_time
        field = booking._meta.get_field('dropoff_time')
        self.assertIsInstance(field, models.TimeField)
        self.assertIsInstance(booking.dropoff_time, datetime.time)

        # estimated_pickup_date
        field = booking._meta.get_field('estimated_pickup_date')
        self.assertIsInstance(field, models.DateField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        # Check that it's a date object if set, or None
        self.assertIsInstance(booking.estimated_pickup_date, (datetime.date, type(None)))

        # estimated_pickup_time
        field = booking._meta.get_field('estimated_pickup_time')
        self.assertIsInstance(field, models.TimeField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        # Check that it's a time object if set, or None
        self.assertIsInstance(booking.estimated_pickup_time, (datetime.time, type(None)))

        # booking_status
        field = booking._meta.get_field('booking_status')
        self.assertEqual(field.max_length, 30)
        self.assertEqual(field.default, 'PENDING_CONFIRMATION')
        self.assertGreater(len(field.choices), 0)

        # customer_notes
        field = booking._meta.get_field('customer_notes')
        self.assertIsInstance(field, models.TextField)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # created_at, updated_at
        field = booking._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)
        field = booking._meta.get_field('updated_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now)

    def test_booking_reference_unique_constraint(self):
        """
        Test that booking_reference enforces uniqueness.
        """
        # Create a booking with a specific reference
        existing_booking = ServiceBookingFactory(booking_reference="SERVICE-TESTREF")
        
        # Attempt to create another booking with the same booking_reference
        with self.assertRaises(IntegrityError) as cm:
            ServiceBookingFactory(booking_reference="SERVICE-TESTREF")
        self.assertIn("unique constraint failed", str(cm.exception).lower())

    def test_stripe_payment_intent_id_unique_constraint(self):
        """
        Test that stripe_payment_intent_id enforces uniqueness.
        """
        # Create a booking with a specific stripe_payment_intent_id
        existing_booking = ServiceBookingFactory(stripe_payment_intent_id="pi_test_intent_123")

        # Attempt to create another booking with the same stripe_payment_intent_id
        with self.assertRaises(IntegrityError) as cm:
            ServiceBookingFactory(stripe_payment_intent_id="pi_test_intent_123")
        self.assertIn("unique constraint failed", str(cm.exception).lower())


    def test_default_values(self):
        """
        Test that default values are correctly applied when not explicitly set.
        """
        # Create a booking with minimal required fields
        service_type = ServiceTypeFactory()
        service_profile = ServiceProfileFactory()
        dropoff_date = datetime.date.today() + datetime.timedelta(days=7)
        dropoff_time = datetime.time(10, 0, 0)

        booking = ServiceBooking.objects.create(
            service_type=service_type,
            service_profile=service_profile,
            dropoff_date=dropoff_date,
            dropoff_time=dropoff_time,
        )

        self.assertEqual(booking.calculated_total, Decimal('0.00'))
        self.assertEqual(booking.calculated_deposit_amount, Decimal('0.00'))
        self.assertEqual(booking.amount_paid, Decimal('0.00'))
        self.assertEqual(booking.payment_status, 'unpaid')
        self.assertEqual(booking.currency, 'AUD')
        self.assertEqual(booking.booking_status, 'PENDING_CONFIRMATION')
        self.assertIsNone(booking.customer_motorcycle)
        self.assertIsNone(booking.payment_option)
        self.assertIsNone(booking.payment)
        self.assertIsNone(booking.payment_method)
        self.assertIsNone(booking.stripe_payment_intent_id)
        self.assertIsNone(booking.estimated_pickup_date)
        self.assertIsNone(booking.estimated_pickup_time)
        # FIX: customer_notes is null=True, so it should be None
        self.assertIsNone(booking.customer_notes) 

    def test_timestamps_auto_now_add_and_auto_now(self):
        """
        Test that created_at is set on creation and updated_at is updated on save.
        """
        booking = ServiceBookingFactory()
        initial_created_at = booking.created_at
        initial_updated_at = booking.updated_at

        # created_at should be set on creation
        self.assertIsNotNone(initial_created_at)
        self.assertIsNotNone(initial_updated_at)
        # For auto_now_add and auto_now fields, they might be very close,
        # but created_at should be slightly before or equal to updated_at initially
        self.assertLessEqual(initial_created_at, initial_updated_at)

        # Update the booking and save
        import time
        time.sleep(0.01) # Ensure a slight time difference for updated_at to change
        booking.customer_notes = "Updated notes for timestamp test."
        booking.save()

        # updated_at should be greater than its initial value
        self.assertGreater(booking.updated_at, initial_updated_at)
        # created_at should remain the same
        self.assertEqual(booking.created_at, initial_created_at)

    def test_related_name_accessors(self):
        """
        Test that related_name accessors work as expected.
        """
        service_type = ServiceTypeFactory()
        service_profile = ServiceProfileFactory()
        customer_motorcycle = CustomerMotorcycleFactory(service_profile=service_profile)
        payment = PaymentFactory()

        booking = ServiceBookingFactory(
            service_type=service_type,
            service_profile=service_profile,
            customer_motorcycle=customer_motorcycle,
            payment=payment
        )

        # Test reverse relationships
        self.assertIn(booking, service_type.service_bookings.all())
        self.assertIn(booking, service_profile.service_bookings.all())
        self.assertIn(booking, customer_motorcycle.service_bookings.all())
        self.assertEqual(booking, payment.related_service_booking_payment)

    def test_on_delete_behavior(self):
        """
        Test the on_delete behavior for foreign keys.
        """
        # PROTECT for service_type
        # Create a new service type and booking to ensure isolation for this test
        service_type_for_protect = ServiceTypeFactory()
        booking_for_protect_test = ServiceBookingFactory(service_type=service_type_for_protect)
        
        with self.assertRaises(models.ProtectedError):
            service_type_for_protect.delete()
        
        # CASCADE for service_profile
        # Create a new service profile and booking for this test
        service_profile_for_cascade = ServiceProfileFactory()
        booking_for_cascade_test = ServiceBookingFactory(service_profile=service_profile_for_cascade)
        booking_id_for_cascade = booking_for_cascade_test.id
        
        service_profile_for_cascade.delete()
        
        # The service booking should be deleted if its service profile is deleted
        self.assertFalse(ServiceBooking.objects.filter(id=booking_id_for_cascade).exists())
        
        # SET_NULL for customer_motorcycle and payment
        # Recreate a booking for this test
        booking_for_null_test = ServiceBookingFactory()
        customer_motorcycle = booking_for_null_test.customer_motorcycle
        payment = booking_for_null_test.payment

        customer_motorcycle.delete()
        payment.delete()

        booking_for_null_test.refresh_from_db()
        self.assertIsNone(booking_for_null_test.customer_motorcycle)
        self.assertIsNone(booking_for_null_test.payment)