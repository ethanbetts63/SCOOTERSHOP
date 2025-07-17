from django.test import TestCase
from datetime import date, time, timedelta


from service.utils.admin_create_service_booking import admin_create_service_booking


from service.models import ServiceBooking


from inventory.forms.admin_motorcycle_form import MotorcycleForm
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, TempSalesBookingFactory, SalesProfileFactory, MotorcycleConditionFactory, MotorcycleFactory, MotorcycleImageFactory, FeaturedMotorcycleFactory, InventorySettingsFactory, BlockedSalesDateFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory



class AdminCreateServiceBookingTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(
            service_profile=cls.service_profile
        )

    def test_booking_creation_with_all_fields(self):

        today = date.today()
        future_service_date = today.replace(year=today.year + 1)
        future_dropoff_date = future_service_date
        dropoff_time = time(9, 30)
        estimated_pickup_date = future_service_date + timedelta(days=3)

        admin_booking_form_data = {
            "service_type": self.service_type,
            "service_date": future_service_date,
            "dropoff_date": future_dropoff_date,
            "dropoff_time": dropoff_time,
            "customer_notes": "Customer requested synthetic oil.",
            "booking_status": ServiceBooking.BOOKING_STATUS_CHOICES[1][0],
            "payment_status": ServiceBooking.PAYMENT_STATUS_CHOICES[0][0],
            "estimated_pickup_date": estimated_pickup_date,
        }

        booking = admin_create_service_booking(
            admin_booking_form_data,
            self.service_profile,
            self.customer_motorcycle,
        )

        self.assertIsInstance(booking, ServiceBooking)
        self.assertIsNotNone(booking.pk)
        self.assertIsNotNone(booking.service_booking_reference)

        self.assertEqual(booking.service_type, self.service_type)
        self.assertEqual(booking.service_date, future_service_date)
        self.assertEqual(booking.dropoff_date, future_dropoff_date)
        self.assertEqual(booking.dropoff_time, dropoff_time)
        self.assertEqual(booking.customer_notes, "Customer requested synthetic oil.")

        self.assertEqual(booking.booking_status, "confirmed")
        self.assertEqual(booking.payment_status, "unpaid")
        self.assertEqual(booking.estimated_pickup_date, estimated_pickup_date)

        self.assertEqual(booking.service_profile, self.service_profile)
        self.assertEqual(booking.customer_motorcycle, self.customer_motorcycle)

    def test_booking_creation_with_optional_fields_missing(self):

        today = date.today()
        future_service_date = today.replace(year=today.year + 1)
        future_dropoff_date = future_service_date
        dropoff_time = time(10, 0)

        admin_booking_form_data = {
            "service_type": self.service_type,
            "service_date": future_service_date,
            "dropoff_date": future_dropoff_date,
            "dropoff_time": dropoff_time,
            "booking_status": ServiceBooking.BOOKING_STATUS_CHOICES[0][0],
            "payment_status": ServiceBooking.PAYMENT_STATUS_CHOICES[0][0],
        }

        booking = admin_create_service_booking(
            admin_booking_form_data,
            self.service_profile,
            self.customer_motorcycle,
        )

        self.assertIsInstance(booking, ServiceBooking)
        self.assertIsNotNone(booking.pk)
        self.assertIsNotNone(booking.service_booking_reference)

        self.assertEqual(booking.service_type, self.service_type)
        self.assertEqual(booking.service_date, future_service_date)
        self.assertEqual(booking.dropoff_date, future_dropoff_date)
        self.assertEqual(booking.dropoff_time, dropoff_time)
        self.assertEqual(booking.booking_status, "pending")
        self.assertEqual(booking.payment_status, "unpaid")

        self.assertEqual(booking.customer_notes, "")

        self.assertIsNone(booking.estimated_pickup_date)

        self.assertEqual(booking.service_profile, self.service_profile)
        self.assertEqual(booking.customer_motorcycle, self.customer_motorcycle)

    def test_booking_status_and_payment_status_options(self):

        today = date.today()
        future_date = today + timedelta(days=10)
        dropoff_time = time(11, 0)

        admin_booking_form_data_completed = {
            "service_type": self.service_type,
            "service_date": future_date,
            "dropoff_date": future_date,
            "dropoff_time": dropoff_time,
            "booking_status": "completed",
            "payment_status": "paid",
        }
        booking_completed = admin_create_service_booking(
            admin_booking_form_data_completed,
            self.service_profile,
            self.customer_motorcycle,
        )
        self.assertEqual(booking_completed.booking_status, "completed")
        self.assertEqual(booking_completed.payment_status, "paid")

        admin_booking_form_data_declined = {
            "service_type": self.service_type,
            "service_date": future_date,
            "dropoff_date": future_date,
            "dropoff_time": dropoff_time,
            "booking_status": "declined",
            "payment_status": "refunded",
        }
        booking_declined = admin_create_service_booking(
            admin_booking_form_data_declined,
            self.service_profile,
            self.customer_motorcycle,
        )
        self.assertEqual(booking_declined.booking_status, "declined")
        self.assertEqual(booking_declined.payment_status, "refunded")

    def test_service_booking_reference_generation(self):

        today = date.today()
        future_date = today.replace(year=today.year + 1)
        dropoff_time = time(12, 0)

        admin_booking_form_data = {
            "service_type": self.service_type,
            "service_date": future_date,
            "dropoff_date": future_date,
            "dropoff_time": dropoff_time,
            "booking_status": ServiceBooking.BOOKING_STATUS_CHOICES[0][0],
            "payment_status": ServiceBooking.PAYMENT_STATUS_CHOICES[0][0],
        }

        booking = admin_create_service_booking(
            admin_booking_form_data, self.service_profile, self.customer_motorcycle
        )
        self.assertIsNotNone(booking.service_booking_reference)
        self.assertTrue(booking.service_booking_reference.startswith("SVC-"))
        self.assertEqual(len(booking.service_booking_reference), 12)
