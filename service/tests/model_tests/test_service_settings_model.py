from django.test import TestCase
from django.db import models, IntegrityError
from decimal import Decimal
import datetime
from faker import Faker

fake = Faker()


from service.models import ServiceBooking


from ..test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    PaymentFactory,
)


class ServiceBookingModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        test_dropoff_date = fake.date_between(start_date="today", end_date="+30d")
        test_dropoff_time = fake.time_object()

        test_service_date = test_dropoff_date + datetime.timedelta(
            days=fake.random_int(min=0, max=7)
        )

        cls.service_booking = ServiceBookingFactory(
            service_date=test_service_date,
            dropoff_date=test_dropoff_date,
            dropoff_time=test_dropoff_time,
        )

    def test_service_booking_creation(self):

        self.assertIsNotNone(self.service_booking)
        self.assertIsInstance(self.service_booking, ServiceBooking)
        self.assertEqual(ServiceBooking.objects.count(), 1)

    def test_service_booking_reference_generation_on_save(self):

        booking = ServiceBookingFactory()

        self.assertIsNotNone(booking.service_booking_reference)
        self.assertNotEqual(booking.service_booking_reference, "")
        self.assertTrue(booking.service_booking_reference.startswith("SERVICE-"))
        self.assertEqual(len(booking.service_booking_reference), 8 + len("SERVICE-"))

        old_reference = booking.service_booking_reference
        booking.customer_notes = "Updated notes"
        booking.save()
        self.assertEqual(booking.service_booking_reference, old_reference)

    def test_str_method(self):

        expected_str = f"Booking {self.service_booking.service_booking_reference} for {self.service_booking.service_profile.name} on {self.service_booking.dropoff_date}"
        self.assertEqual(str(self.service_booking), expected_str)

    def test_field_attributes(self):

        booking = self.service_booking

        field = booking._meta.get_field("service_booking_reference")
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.unique)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        field = booking._meta.get_field("service_type")
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, "ServiceType")
        self.assertEqual(field.remote_field.on_delete, models.PROTECT)

        field = booking._meta.get_field("service_profile")
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, "ServiceProfile")
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

        field = booking._meta.get_field("customer_motorcycle")
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, "CustomerMotorcycle")
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        field = booking._meta.get_field("payment")
        self.assertIsInstance(field, models.OneToOneField)
        self.assertEqual(field.related_model.__name__, "Payment")
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        for field_name in [
            "calculated_total",
            "calculated_deposit_amount",
            "amount_paid",
        ]:
            field = booking._meta.get_field(field_name)
            self.assertIsInstance(field, models.DecimalField)
            self.assertEqual(field.decimal_places, 2)
            self.assertIsInstance(getattr(booking, field_name), Decimal)
            self.assertGreaterEqual(getattr(booking, field_name), Decimal("0.00"))

        self.assertEqual(booking._meta.get_field("calculated_total").max_digits, 10)
        self.assertEqual(
            booking._meta.get_field("calculated_deposit_amount").max_digits, 8
        )
        self.assertEqual(booking._meta.get_field("amount_paid").max_digits, 10)

        field = booking._meta.get_field("payment_status")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertEqual(field.default, "unpaid")
        self.assertGreater(len(field.choices), 0)

        field = booking._meta.get_field("payment_method")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertGreater(len(field.choices), 0)

        field = booking._meta.get_field("currency")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 3)
        self.assertEqual(field.default, "AUD")

        field = booking._meta.get_field("stripe_payment_intent_id")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 100)
        self.assertTrue(field.unique)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        field = booking._meta.get_field("service_date")
        self.assertIsInstance(field, models.DateField)
        self.assertIsInstance(booking.service_date, datetime.date)

        field = booking._meta.get_field("dropoff_date")
        self.assertIsInstance(field, models.DateField)
        self.assertIsInstance(booking.dropoff_date, datetime.date)

        field = booking._meta.get_field("dropoff_time")
        self.assertIsInstance(field, models.TimeField)
        self.assertIsInstance(booking.dropoff_time, datetime.time)

        field = booking._meta.get_field("estimated_pickup_date")
        self.assertIsInstance(field, models.DateField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        self.assertIsInstance(
            booking.estimated_pickup_date, (datetime.date, type(None))
        )

        field = booking._meta.get_field("booking_status")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 30)
        self.assertEqual(field.default, "PENDING_CONFIRMATION")
        self.assertGreater(len(field.choices), 0)

        field = booking._meta.get_field("customer_notes")
        self.assertIsInstance(field, models.TextField)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        field = booking._meta.get_field("created_at")
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)
        field = booking._meta.get_field("updated_at")
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now)

    def test_service_booking_reference_unique_constraint(self):

        existing_booking = ServiceBookingFactory(
            service_booking_reference="SERVICE-TESTREF"
        )

        with self.assertRaises(IntegrityError) as cm:

            ServiceBookingFactory(
                service_booking_reference="SERVICE-TESTREF",
                service_date=fake.date_between(start_date="today", end_date="+30d"),
                dropoff_date=fake.date_between(start_date="today", end_date="+30d"),
                dropoff_time=fake.time_object(),
            )
        self.assertIn("unique constraint failed", str(cm.exception).lower())

    def test_stripe_payment_intent_id_unique_constraint(self):

        existing_booking = ServiceBookingFactory(
            stripe_payment_intent_id="pi_test_intent_123"
        )

        with self.assertRaises(IntegrityError) as cm:

            ServiceBookingFactory(
                stripe_payment_intent_id="pi_test_intent_123",
                service_date=fake.date_between(start_date="today", end_date="+30d"),
                dropoff_date=fake.date_between(start_date="today", end_date="+30d"),
                dropoff_time=fake.time_object(),
            )
        self.assertIn("unique constraint failed", str(cm.exception).lower())

    def test_default_values(self):

        service_type = ServiceTypeFactory()
        service_profile = ServiceProfileFactory()
        service_date = datetime.date.today() + datetime.timedelta(days=7)
        dropoff_date = datetime.date.today() + datetime.timedelta(days=7)
        dropoff_time = datetime.time(10, 0, 0)

        booking = ServiceBooking.objects.create(
            service_type=service_type,
            service_profile=service_profile,
            service_date=service_date,
            dropoff_date=dropoff_date,
            dropoff_time=dropoff_time,
        )

        self.assertEqual(booking.calculated_total, Decimal("0.00"))
        self.assertEqual(booking.calculated_deposit_amount, Decimal("0.00"))
        self.assertEqual(booking.amount_paid, Decimal("0.00"))
        self.assertEqual(booking.payment_status, "unpaid")
        self.assertEqual(booking.currency, "AUD")
        self.assertEqual(booking.booking_status, "PENDING_CONFIRMATION")
        self.assertIsNone(booking.customer_motorcycle)
        self.assertIsNone(booking.payment)
        self.assertIsNone(booking.payment_method)
        self.assertIsNone(booking.stripe_payment_intent_id)
        self.assertIsNone(booking.estimated_pickup_date)
        self.assertIsNone(booking.customer_notes)

    def test_timestamps_auto_now_add_and_auto_now(self):

        booking = ServiceBookingFactory()
        initial_created_at = booking.created_at
        initial_updated_at = booking.updated_at

        self.assertIsNotNone(initial_created_at)
        self.assertIsNotNone(initial_updated_at)

        self.assertLessEqual(initial_created_at, initial_updated_at)

        import time

        time.sleep(0.01)
        booking.customer_notes = "Updated notes for timestamp test."
        booking.save()

        self.assertGreater(booking.updated_at, initial_updated_at)

        self.assertEqual(booking.created_at, initial_created_at)

    def test_related_name_accessors(self):

        service_type = ServiceTypeFactory()
        service_profile = ServiceProfileFactory()
        customer_motorcycle = CustomerMotorcycleFactory(service_profile=service_profile)
        payment = PaymentFactory()

        booking = ServiceBookingFactory(
            service_type=service_type,
            service_profile=service_profile,
            customer_motorcycle=customer_motorcycle,
            payment=payment,
        )

        self.assertIn(booking, service_type.service_bookings.all())
        self.assertIn(booking, service_profile.service_bookings.all())
        self.assertIn(booking, customer_motorcycle.service_bookings.all())
        self.assertEqual(booking, payment.related_service_booking_payment)

    def test_on_delete_behavior(self):

        service_type_for_protect = ServiceTypeFactory()
        booking_for_protect_test = ServiceBookingFactory(
            service_type=service_type_for_protect
        )

        with self.assertRaises(models.ProtectedError):
            service_type_for_protect.delete()

        service_profile_for_cascade = ServiceProfileFactory()
        booking_for_cascade_test = ServiceBookingFactory(
            service_profile=service_profile_for_cascade
        )
        booking_id_for_cascade = booking_for_cascade_test.id

        service_profile_for_cascade.delete()

        self.assertFalse(
            ServiceBooking.objects.filter(id=booking_id_for_cascade).exists()
        )

        booking_for_null_test = ServiceBookingFactory()
        customer_motorcycle = booking_for_null_test.customer_motorcycle
        payment = booking_for_null_test.payment

        customer_motorcycle.delete()
        payment.delete()

        booking_for_null_test.refresh_from_db()
        self.assertIsNone(booking_for_null_test.customer_motorcycle)
        self.assertIsNone(booking_for_null_test.payment)
