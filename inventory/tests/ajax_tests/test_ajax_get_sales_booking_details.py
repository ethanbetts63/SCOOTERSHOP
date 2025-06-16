from django.test import TestCase, Client, override_settings
from django.urls import reverse
from unittest import mock
from decimal import Decimal
from django.utils import timezone
import datetime

from inventory.tests.test_helpers.model_factories import (
    UserFactory, SalesBookingFactory, SalesProfileFactory, PaymentFactory,
    MotorcycleFactory, RefundRequestFactory
)

@override_settings(
    SITE_BASE_URL='http://test.com',
    ADMIN_EMAIL='admin@example.com',
    DEFAULT_FROM_EMAIL='noreply@example.com',
)
class AjaxGetSalesBookingDetailsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.regular_user = UserFactory(is_staff=False)
        self.ajax_url_name = 'inventory:api_sales_booking_details' # Assuming this URL name exists in your inventory.urls

    def test_permission_denied_for_non_staff_user(self):
        self.client.force_login(self.regular_user)
        sales_booking = SalesBookingFactory()
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {'error': 'Permission denied'})

    def test_sales_booking_not_found(self):
        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[99999]) # Non-existent PK
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(response.content, {'error': 'Sales Booking not found'})

    @mock.patch('inventory.ajax.ajax_get_sales_booking_details.calculate_sales_refund_amount')
    def test_successful_retrieval_with_user_profile(self, mock_calculate_sales_refund_amount):
        mock_calculate_sales_refund_amount.return_value = {
            'entitled_amount': Decimal('100.00'),
            'details': 'Full refund due.',
            'policy_applied': 'Full Refund Policy',
            'time_since_booking_creation_hours': 10.0,
        }

        user = UserFactory(email='customer@example.com', first_name='John', last_name='Doe')
        # SalesProfile name and email are non-nullable, so provide them
        sales_profile = SalesProfileFactory(user=user, name=f"{user.first_name} {user.last_name}", email=user.email)
        motorcycle = MotorcycleFactory(vin_number='VIN1234567890ABCDEF')
        payment = PaymentFactory(amount=Decimal('200.00'), status='succeeded')
        sales_booking = SalesBookingFactory(
            sales_profile=sales_profile,
            motorcycle=motorcycle, # Motorcycle is non-nullable, so always provide one
            payment=payment,
            customer_notes='Test notes',
            request_viewing=True,
            appointment_date=datetime.date(2025, 1, 15),
            appointment_time=datetime.time(10, 0)
        )
        # Ensure the payment created_at is in the past for time_since_booking_creation_hours
        payment.created_at = timezone.now() - datetime.timedelta(hours=10)
        payment.save()


        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        # Corrected assertion: id is an integer in the JSON response
        self.assertEqual(json_response['id'], sales_booking.id)
        self.assertEqual(json_response['sales_booking_reference'], sales_booking.sales_booking_reference)
        self.assertEqual(json_response['customer_name'], 'John Doe')
        self.assertEqual(json_response['customer_email'], 'customer@example.com')
        self.assertEqual(json_response['motorcycle_details']['vin'], 'VIN1234567890ABCDEF')
        self.assertEqual(json_response['payment_amount'], 200.00)
        self.assertEqual(json_response['customer_notes'], 'Test notes')
        self.assertTrue(json_response['request_viewing'])
        self.assertEqual(json_response['appointment_date'], '2025-01-15')
        self.assertEqual(json_response['appointment_time'], '10:00')
        self.assertEqual(json_response['entitled_refund_amount'], 100.00)
        self.assertEqual(json_response['refund_calculation_details'], 'Full refund due.')
        self.assertEqual(json_response['refund_policy_applied'], 'Full Refund Policy')
        self.assertAlmostEqual(json_response['time_since_booking_creation_hours'], 10.0, places=5)
        self.assertEqual(json_response['refund_request_status_for_booking'], 'No Refund Request Yet')


    @mock.patch('inventory.ajax.ajax_get_sales_booking_details.calculate_sales_refund_amount')
    def test_successful_retrieval_without_user_profile_email_from_sales_profile(self, mock_calculate_sales_refund_amount):
        mock_calculate_sales_refund_amount.return_value = {
            'entitled_amount': Decimal('50.00'),
            'details': 'Partial refund.',
            'policy_applied': 'Partial Refund Policy',
            'time_since_booking_creation_hours': 24.0,
        }

        # SalesProfile name and email are non-nullable, so provide them
        sales_profile = SalesProfileFactory(user=None, name='Anonymous Customer', email='anon@example.com')
        motorcycle = MotorcycleFactory(vin_number='VINANON1234567890')
        payment = PaymentFactory(amount=Decimal('150.00'), status='succeeded')
        sales_booking = SalesBookingFactory(
            sales_profile=sales_profile,
            motorcycle=motorcycle, # Motorcycle is non-nullable, so always provide one
            payment=payment
        )

        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['customer_name'], 'Anonymous Customer')
        self.assertEqual(json_response['customer_email'], 'anon@example.com')
        self.assertEqual(json_response['entitled_refund_amount'], 50.00)

    # Removed test_successful_retrieval_without_user_profile_no_email
    # because SalesProfile.name and .email are non-nullable,
    # making it impossible to create such a SalesProfile instance.

    @mock.patch('inventory.ajax.ajax_get_sales_booking_details.calculate_sales_refund_amount')
    def test_refund_request_status_display(self, mock_calculate_sales_refund_amount):
        mock_calculate_sales_refund_amount.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No refund.',
            'policy_applied': 'No Refund Policy',
            'time_since_booking_creation_hours': 72.0,
        }

        sales_booking = SalesBookingFactory()
        # Create a refund request for the sales booking
        RefundRequestFactory(sales_booking=sales_booking, status='approved')

        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['refund_request_status_for_booking'], 'Approved - Awaiting Refund')

    # Removed test_motorcycle_details_n_a_if_no_motorcycle
    # because SalesBooking.motorcycle is non-nullable,
    # making it impossible to create such a SalesBooking instance.

    @mock.patch('inventory.ajax.ajax_get_sales_booking_details.calculate_sales_refund_amount')
    def test_payment_details_n_a_if_no_payment(self, mock_calculate_sales_refund_amount):
        mock_calculate_sales_refund_amount.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No refund.',
            'policy_applied': 'No Refund Policy',
            'time_since_booking_creation_hours': 0.0,
        }
        # Create a sales booking with no associated payment
        sales_booking = SalesBookingFactory(payment=None)

        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['payment_date'], 'N/A')
        self.assertEqual(json_response['payment_amount'], 'N/A')

    @mock.patch('inventory.ajax.ajax_get_sales_booking_details.calculate_sales_refund_amount')
    def test_appointment_details_n_a_if_none(self, mock_calculate_sales_refund_amount):
        mock_calculate_sales_refund_amount.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No refund.',
            'policy_applied': 'No Refund Policy',
            'time_since_booking_creation_hours': 0.0,
        }
        sales_booking = SalesBookingFactory(
            appointment_date=None,
            appointment_time=None,
            customer_notes=None, # Also test None for customer_notes
            request_viewing=False # Test false for request_viewing
        )

        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)
        json_response = response.json()

        self.assertEqual(json_response['appointment_date'], 'N/A')
        self.assertEqual(json_response['appointment_time'], 'N/A')
        self.assertEqual(json_response['customer_notes'], '') # Should default to empty string
        self.assertFalse(json_response['request_viewing'])

    @mock.patch('inventory.ajax.ajax_get_sales_booking_details.calculate_sales_refund_amount')
    def test_exception_handling(self, mock_calculate_sales_refund_amount):
        mock_calculate_sales_refund_amount.side_effect = Exception("Test calculation error")

        sales_booking = SalesBookingFactory()

        self.client.force_login(self.admin_user)
        url = reverse(self.ajax_url_name, args=[sales_booking.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        self.assertIn('An unexpected error occurred: Test calculation error', response.json()['error'])
