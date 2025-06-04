from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, time, timedelta
from django.db import models
import uuid

# Import the TempServiceBooking model
from service.models import TempServiceBooking

# Import the factories
from ..test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory
)

class TempServiceBookingModelTest(TestCase):
    """
    Tests for the TempServiceBooking model, including field validations,
    unique constraints, and foreign key relationships.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We create foreign key instances here to ensure they are saved
        in the database when building TempServiceBooking instances for full_clean tests.
        """
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile) # Link to the created service_profile
        cls.temp_booking = TempServiceBookingFactory(
            service_type=cls.service_type,
            service_profile=cls.service_profile,
            customer_motorcycle=cls.customer_motorcycle
        )

    def test_temp_service_booking_creation(self):
        """
        Test that a TempServiceBooking instance can be created using the factory.
        """
        self.assertIsNotNone(self.temp_booking)
        self.assertIsInstance(self.temp_booking, TempServiceBooking)
        # We created one in setUpTestData, so count should be 1
        self.assertEqual(TempServiceBooking.objects.count(), 1)

    def test_str_method(self):
        """
        Test the __str__ method of the TempServiceBooking model.
        """
        # The __str__ method uses session_uuid, service_profile.name, and dropoff_date
        expected_str = (
            f"Temp Booking {self.temp_booking.session_uuid} for "
            f"{self.temp_booking.service_profile.name} on {self.temp_booking.dropoff_date}"
        )
        self.assertEqual(str(self.temp_booking), expected_str)

    def test_field_attributes(self):
        """
        Test the attributes of various fields in the TempServiceBooking model.
        """
        booking = self.temp_booking

        # session_uuid
        field = booking._meta.get_field('session_uuid')
        self.assertIsInstance(field, models.UUIDField)
        self.assertFalse(field.editable)
        self.assertTrue(field.unique)
        self.assertIsNotNone(field.default) # Should have a default UUID

        # service_type
        field = booking._meta.get_field('service_type')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceType')
        self.assertEqual(field.remote_field.on_delete, models.PROTECT)
        self.assertFalse(field.null) # Should be required
        self.assertFalse(field.blank)

        # service_profile
        field = booking._meta.get_field('service_profile')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceProfile')
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)
        self.assertFalse(field.null) # Should be required
        self.assertFalse(field.blank)

        # customer_motorcycle
        field = booking._meta.get_field('customer_motorcycle')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'CustomerMotorcycle')
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # payment_option
        field = booking._meta.get_field('payment_option')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertGreater(len(field.choices), 0)

        # dropoff_date
        field = booking._meta.get_field('dropoff_date')
        self.assertIsInstance(field, models.DateField)
        self.assertFalse(field.null)
        self.assertFalse(field.blank)

        # dropoff_time
        field = booking._meta.get_field('dropoff_time')
        self.assertIsInstance(field, models.TimeField)
        self.assertFalse(field.null)
        self.assertFalse(field.blank)

        # estimated_pickup_date
        field = booking._meta.get_field('estimated_pickup_date')
        self.assertIsInstance(field, models.DateField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # estimated_pickup_time
        field = booking._meta.get_field('estimated_pickup_time')
        self.assertIsInstance(field, models.TimeField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # customer_notes
        field = booking._meta.get_field('customer_notes')
        self.assertIsInstance(field, models.TextField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # calculated_deposit_amount
        field = booking._meta.get_field('calculated_deposit_amount')
        self.assertIsInstance(field, models.DecimalField)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # created_at, updated_at
        field = booking._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)
        field = booking._meta.get_field('updated_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now)

    def test_required_fields_validation(self):
        """
        Test that required fields (service_type, service_profile, dropoff_date, dropoff_time)
        raise ValidationError when missing.
        """
        # Test missing service_type
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=None,
                service_profile=self.service_profile, # Provide required FK
                dropoff_date=date.today(),
                dropoff_time=time(9,0)
            ).full_clean()
        self.assertIn('service_type', cm.exception.message_dict)

        # Test missing service_profile
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=self.service_type, # Provide required FK
                service_profile=None,
                dropoff_date=date.today(),
                dropoff_time=time(9,0)
            ).full_clean()
        self.assertIn('service_profile', cm.exception.message_dict)

        # Test missing dropoff_date
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                dropoff_date=None,
                dropoff_time=time(9,0)
            ).full_clean()
        self.assertIn('dropoff_date', cm.exception.message_dict)

        # Test missing dropoff_time
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                dropoff_date=date.today(),
                dropoff_time=None
            ).full_clean()
        self.assertIn('dropoff_time', cm.exception.message_dict)

        # Test all required fields present (should pass)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly: {e.message_dict}")

    def test_session_uuid_uniqueness(self):
        """
        Test that session_uuid enforces uniqueness.
        """
        # Create a booking with a specific UUID
        first_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile
        )
        
        # Attempt to create another booking with the same UUID
        with self.assertRaises(IntegrityError):
            # We need to use .create() here to hit the database unique constraint
            TempServiceBookingFactory.create(
                session_uuid=first_booking.session_uuid,
                service_type=self.service_type,
                service_profile=self.service_profile
            )

    def test_payment_option_choices(self):
        """
        Test that payment_option only accepts valid choices.
        """
        # Test with a valid choice
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                payment_option='online_full'
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for valid payment_option: {e.message_dict}")

        # Test with an invalid choice
        with self.assertRaises(ValidationError) as cm:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                payment_option='invalid_option'
            ).full_clean()
        self.assertIn('payment_option', cm.exception.message_dict)
        self.assertIn("Value 'invalid_option' is not a valid choice.", str(cm.exception))

        # Test with None (allowed)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                payment_option=None
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None payment_option: {e.message_dict}")

    def test_dropoff_date_not_in_past(self):
        """
        Test that dropoff_date cannot be in the past.
        Note: Django's DateField does not have built-in future/past validation.
        This would typically be handled in a form's clean method or custom model validation.
        For now, we'll assume the model itself doesn't enforce this, but a form would.
        If a custom clean method were added to TempServiceBooking, this test would change.
        """
        # Create a booking with a past date (should not raise ValidationError at model level without custom clean)
        past_date = date.today() - timedelta(days=1)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                dropoff_date=past_date
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised for past dropoff_date, but model doesn't enforce this.")

        # Test with current date (should pass)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                dropoff_date=date.today()
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for current dropoff_date: {e.message_dict}")

        # Test with future date (should pass)
        future_date = date.today() + timedelta(days=7)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                dropoff_date=future_date
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for future dropoff_date: {e.message_dict}")

    def test_calculated_deposit_amount_validation(self):
        """
        Test that calculated_deposit_amount cannot be negative if provided.
        Note: DecimalField allows negative values by default. This validation
        would typically be in a form or custom model clean method.
        """
        # Test with a negative amount (should not raise ValidationError at model level without custom clean)
        negative_amount = -10.50
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=negative_amount
            ).full_clean()
        except ValidationError:
            self.fail("ValidationError raised for negative calculated_deposit_amount, but model doesn't enforce this.")

        # Test with zero (should pass)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=0.00
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for zero calculated_deposit_amount: {e.message_dict}")

        # Test with positive amount (should pass)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=50.00
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for positive calculated_deposit_amount: {e.message_dict}")

        # Test with None (allowed)
        try:
            TempServiceBookingFactory.build(
                service_type=self.service_type,
                service_profile=self.service_profile,
                calculated_deposit_amount=None
            ).full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None calculated_deposit_amount: {e.message_dict}")


    def test_timestamps_auto_now_add_and_auto_now(self):
        """
        Test that created_at is set on creation and updated_at is updated on save.
        """
        booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile
        )
        initial_created_at = booking.created_at
        initial_updated_at = booking.updated_at

        # created_at should be set on creation
        self.assertIsNotNone(initial_created_at)
        self.assertIsNotNone(initial_updated_at)
        self.assertLessEqual(initial_created_at, initial_updated_at)

        # Update the booking and save
        import time
        time.sleep(0.01) # Ensure a slight time difference for updated_at to change
        booking.customer_notes = "Updated notes"
        booking.save()

        # updated_at should be greater than its initial value
        self.assertGreater(booking.updated_at, initial_updated_at)
        # created_at should remain the same
        self.assertEqual(booking.created_at, initial_created_at)

    def test_foreign_key_on_delete_service_type(self):
        """
        Test that deleting a ServiceType prevents deletion of TempServiceBooking (PROTECT).
        """
        # Create a new booking with a specific service type for this test
        service_type_to_delete = ServiceTypeFactory()
        booking_to_test = TempServiceBookingFactory(
            service_type=service_type_to_delete,
            service_profile=self.service_profile # Use existing service_profile
        )
        
        with self.assertRaises(models.ProtectedError):
            service_type_to_delete.delete()
        
        # Ensure the booking still exists
        self.assertTrue(TempServiceBooking.objects.filter(pk=booking_to_test.pk).exists())

    def test_foreign_key_on_delete_service_profile(self):
        """
        Test that deleting a ServiceProfile cascades and deletes TempServiceBooking (CASCADE).
        """
        # Create a new service profile and booking for this test
        service_profile_to_delete = ServiceProfileFactory()
        booking_to_test = TempServiceBookingFactory(
            service_profile=service_profile_to_delete,
            service_type=self.service_type # Use existing service_type
        )
        
        # Delete the service profile
        service_profile_to_delete.delete()
        
        # Ensure the booking is also deleted
        self.assertFalse(TempServiceBooking.objects.filter(pk=booking_to_test.pk).exists())

    def test_foreign_key_on_delete_customer_motorcycle(self):
        """
        Test that deleting a CustomerMotorcycle sets the customer_motorcycle field to NULL (SET_NULL).
        """
        # Create a new booking with a customer motorcycle explicitly
        customer_motorcycle_to_delete = CustomerMotorcycleFactory(service_profile=self.service_profile)
        booking_with_motorcycle = TempServiceBookingFactory(
            customer_motorcycle=customer_motorcycle_to_delete,
            service_type=self.service_type,
            service_profile=self.service_profile
        )
        
        # Delete the customer motorcycle
        customer_motorcycle_to_delete.delete()
        
        # Refresh the booking instance from the database
        booking_with_motorcycle.refresh_from_db()
        
        # Ensure customer_motorcycle is set to None
        self.assertIsNone(booking_with_motorcycle.customer_motorcycle)
        # Ensure the booking itself still exists
        self.assertTrue(TempServiceBooking.objects.filter(pk=booking_with_motorcycle.pk).exists())

