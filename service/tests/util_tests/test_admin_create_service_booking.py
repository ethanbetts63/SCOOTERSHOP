from django.test import TestCase
from datetime import date, time, timedelta
# Removed: from django.contrib.auth import get_user_model # No longer needed as created_by is removed

# Import the utility function to be tested
from service.utils.admin_create_service_booking import admin_create_service_booking

# Import models and factories
from service.models import ServiceBooking
from ..test_helpers.model_factories import (
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    # Removed: UserFactory, # No longer needed as created_by is removed
)

# Removed: User = get_user_model() # No longer needed

class AdminCreateServiceBookingTest(TestCase):
    """
    Tests for the `admin_create_service_booking` utility function.
    This suite verifies that ServiceBooking instances are created correctly
    based on the input data and associated objects, after removing
    `admin_notes` and `created_by` fields from the model and utility.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data for all tests in this class.
        Create necessary related objects using factories.
        """
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)
        # Removed: cls.admin_user = UserFactory(is_staff=True) # No longer needed

    def test_booking_creation_with_all_fields(self):
        """
        Test that a ServiceBooking is created successfully when all data,
        including optional fields (that still exist), is provided.
        """
        today = date.today()
        future_service_date = today.replace(year=today.year + 1)
        future_dropoff_date = future_service_date
        dropoff_time = time(9, 30)
        estimated_pickup_date = future_service_date + timedelta(days=3)

        admin_booking_form_data = {
            'service_type': self.service_type,
            'service_date': future_service_date,
            'dropoff_date': future_dropoff_date,
            'dropoff_time': dropoff_time,
            'customer_notes': 'Customer requested synthetic oil.',
            # Removed: 'admin_notes': 'Checked fluid levels.',
            'booking_status': ServiceBooking.BOOKING_STATUS_CHOICES[1][0], # 'confirmed'
            'payment_status': ServiceBooking.PAYMENT_STATUS_CHOICES[0][0], # 'unpaid'
            'estimated_pickup_date': estimated_pickup_date,
        }

        # Call the utility function (removed created_by_user argument)
        booking = admin_create_service_booking(
            admin_booking_form_data,
            self.service_profile,
            self.customer_motorcycle,
            # Removed: self.admin_user
        )

        # Assertions
        self.assertIsInstance(booking, ServiceBooking)
        self.assertIsNotNone(booking.pk)
        self.assertIsNotNone(booking.service_booking_reference)

        self.assertEqual(booking.service_type, self.service_type)
        self.assertEqual(booking.service_date, future_service_date)
        self.assertEqual(booking.dropoff_date, future_dropoff_date)
        self.assertEqual(booking.dropoff_time, dropoff_time)
        self.assertEqual(booking.customer_notes, 'Customer requested synthetic oil.')
        # Removed: self.assertEqual(booking.admin_notes, 'Checked fluid levels.')
        self.assertEqual(booking.booking_status, 'confirmed')
        self.assertEqual(booking.payment_status, 'unpaid')
        self.assertEqual(booking.estimated_pickup_date, estimated_pickup_date)

        self.assertEqual(booking.service_profile, self.service_profile)
        self.assertEqual(booking.customer_motorcycle, self.customer_motorcycle)
        # Removed: self.assertEqual(booking.created_by, self.admin_user)

    def test_booking_creation_with_optional_fields_missing(self):
        """
        Test that a ServiceBooking is created successfully when optional fields are missing.
        """
        today = date.today()
        future_service_date = today.replace(year=today.year + 1)
        future_dropoff_date = future_service_date
        dropoff_time = time(10, 0)

        admin_booking_form_data = {
            'service_type': self.service_type,
            'service_date': future_service_date,
            'dropoff_date': future_dropoff_date,
            'dropoff_time': dropoff_time,
            'booking_status': ServiceBooking.BOOKING_STATUS_CHOICES[0][0], # 'pending'
            'payment_status': ServiceBooking.PAYMENT_STATUS_CHOICES[0][0], # 'unpaid'
            # customer_notes, admin_notes, estimated_pickup_date are missing
        }

        # Call the utility function (removed created_by_user argument)
        booking = admin_create_service_booking(
            admin_booking_form_data,
            self.service_profile,
            self.customer_motorcycle,
            # Removed: self.admin_user
        )

        # Assertions
        self.assertIsInstance(booking, ServiceBooking)
        self.assertIsNotNone(booking.pk)
        self.assertIsNotNone(booking.service_booking_reference)

        self.assertEqual(booking.service_type, self.service_type)
        self.assertEqual(booking.service_date, future_service_date)
        self.assertEqual(booking.dropoff_date, future_dropoff_date)
        self.assertEqual(booking.dropoff_time, dropoff_time)
        self.assertEqual(booking.booking_status, 'pending')
        self.assertEqual(booking.payment_status, 'unpaid')

        # Check that optional fields are set to their defaults (empty string or None)
        self.assertEqual(booking.customer_notes, '')
        # Removed: self.assertEqual(booking.admin_notes, '')
        self.assertIsNone(booking.estimated_pickup_date)

        self.assertEqual(booking.service_profile, self.service_profile)
        self.assertEqual(booking.customer_motorcycle, self.customer_motorcycle)
        # Removed: self.assertEqual(booking.created_by, self.admin_user)

    def test_booking_status_and_payment_status_options(self):
        """
        Test that various booking_status and payment_status options can be set.
        """
        today = date.today()
        future_date = today + timedelta(days=10)
        dropoff_time = time(11, 0)

        # Test with 'completed' booking status and 'paid' payment status
        admin_booking_form_data_completed = {
            'service_type': self.service_type,
            'service_date': future_date,
            'dropoff_date': future_date,
            'dropoff_time': dropoff_time,
            'booking_status': 'completed',
            'payment_status': 'paid',
        }
        booking_completed = admin_create_service_booking(
            admin_booking_form_data_completed, self.service_profile, self.customer_motorcycle # Removed admin_user
        )
        self.assertEqual(booking_completed.booking_status, 'completed')
        self.assertEqual(booking_completed.payment_status, 'paid')

        # Test with 'declined' booking status and 'refunded' payment status
        admin_booking_form_data_declined = {
            'service_type': self.service_type,
            'service_date': future_date,
            'dropoff_date': future_date,
            'dropoff_time': dropoff_time,
            'booking_status': 'declined',
            'payment_status': 'refunded',
        }
        booking_declined = admin_create_service_booking(
            admin_booking_form_data_declined, self.service_profile, self.customer_motorcycle # Removed admin_user
        )
        self.assertEqual(booking_declined.booking_status, 'declined')
        self.assertEqual(booking_declined.payment_status, 'refunded')

    def test_service_booking_reference_generation(self):
        """
        Test that service_booking_reference is automatically generated on save
        if not provided.
        """
        today = date.today()
        future_date = today.replace(year=today.year + 1)
        dropoff_time = time(12, 0)

        admin_booking_form_data = {
            'service_type': self.service_type,
            'service_date': future_date,
            'dropoff_date': future_date,
            'dropoff_time': dropoff_time,
            'booking_status': ServiceBooking.BOOKING_STATUS_CHOICES[0][0],
            'payment_status': ServiceBooking.PAYMENT_STATUS_CHOICES[0][0],
        }

        booking = admin_create_service_booking(
            admin_booking_form_data, self.service_profile, self.customer_motorcycle 
        )
        self.assertIsNotNone(booking.service_booking_reference)
        self.assertTrue(booking.service_booking_reference.startswith('SVC-'))
        self.assertEqual(len(booking.service_booking_reference), 12) 
