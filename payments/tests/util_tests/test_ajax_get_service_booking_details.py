# payments/tests/util_tests/test_ajax_get_service_booking_details.py

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from datetime import time, timedelta
from unittest.mock import patch
from django.utils import timezone
from payments.tests.test_helpers.model_factories import (
    ServiceBookingFactory, PaymentFactory, RefundPolicySettingsFactory,
    ServiceProfileFactory, UserFactory, RefundRequestFactory, 
    CustomerMotorcycleFactory, ServiceTypeFactory
)


class AjaxGetServiceBookingDetailsTests(TestCase):
    """
    Tests for the get_service_booking_details_json AJAX view.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified data for all test methods.
        """
        cls.client = Client()
        cls.user = UserFactory(is_staff=True, is_active=True) # Staff user for login_required
        cls.regular_user = UserFactory(is_staff=False, is_active=True) # Non-staff user

        cls.refund_policy_settings = RefundPolicySettingsFactory()
        cls.full_payment_policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_full_payment_full_refund_days': 7,
            'cancellation_full_payment_partial_refund_days': 3,
            'cancellation_full_payment_partial_refund_percentage': str(Decimal('50.00')),
            'cancellation_full_payment_minimal_refund_days': 1,
            'cancellation_full_payment_minimal_refund_percentage': str(Decimal('10.00')),
        }
        cls.deposit_payment_policy_snapshot = {
            'deposit_enabled': True,
            'cancellation_deposit_full_refund_days': 10,
            'cancellation_deposit_partial_refund_days': 5,
            'cancellation_deposit_partial_refund_percentage': str(Decimal('75.00')),
            'cancellation_deposit_minimal_refund_days': 2,
            'cancellation_deposit_minimal_refund_percentage': str(Decimal('20.00')),
        }

    def setUp(self):
        """
        Log in the staff user for each test that requires it.
        """
        self.client.force_login(self.user)

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_successful_retrieval_full_payment(self, mock_calculate_refund):
        """
        Tests successful retrieval of service booking details for a full payment.
        """
        # Mock the refund calculation result
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('125.00'),
            'details': "Cancellation 4 days before drop-off. Policy: Full Payment Policy: Partial Refund Policy (50.00%). Calculated: 125.00 (50.00% of 250.00).",
            'policy_applied': "Full Payment Policy: Partial Refund Policy (50.00%)",
            'days_before_dropoff': 4,
        }

        # Create a specific user with the desired name
        user_john_doe = UserFactory(first_name="John", last_name="Doe")
        # Create service_profile linked to this user
        service_profile = ServiceProfileFactory(user=user_john_doe, name="Fallback Name")
        customer_motorcycle = CustomerMotorcycleFactory(brand="Honda", model="CBR500R", year=2022)
        service_type = ServiceTypeFactory(name="Oil Change", description="Standard oil change service")
        payment = PaymentFactory(
            amount=Decimal('250.00'),
            status='succeeded',
            created_at=timezone.now() - timedelta(days=1),
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        # Create a service booking
        dropoff_date_in_future = timezone.now().date() + timedelta(days=5) # Adjusted for 4 full days
        booking = ServiceBookingFactory(
            service_profile=service_profile,
            customer_motorcycle=customer_motorcycle,
            service_type=service_type,
            payment=payment,
            payment_method='online_full',
            payment_status='paid',
            calculated_total=Decimal('250.00'),
            amount_paid=Decimal('250.00'),
            dropoff_date=dropoff_date_in_future,
            dropoff_time=time(9, 0),
            estimated_pickup_date=dropoff_date_in_future + timedelta(days=1),
            booking_status='confirmed',
            customer_notes='Please check brakes.',
        )

        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        # ServiceBooking uses AutoField (integer), so 'id' will be an integer.
        self.assertEqual(json_response['id'], booking.id) # Compare integer with integer
        self.assertEqual(json_response['service_booking_reference'], booking.service_booking_reference)
        self.assertEqual(json_response['customer_name'], "John Doe")
        self.assertEqual(json_response['service_date'], booking.service_date.strftime('%Y-%m-%d'))
        self.assertEqual(json_response['dropoff_date'], booking.dropoff_date.strftime('%Y-%m-%d'))
        self.assertEqual(json_response['dropoff_time'], booking.dropoff_time.strftime('%H:%M'))
        self.assertEqual(json_response['estimated_pickup_date'], booking.estimated_pickup_date.strftime('%Y-%m-%d'))
        self.assertEqual(json_response['motorcycle_details']['brand'], "Honda")
        self.assertEqual(json_response['service_type_details']['name'], "Oil Change")
        self.assertEqual(json_response['payment_option'], booking.get_payment_option_display())
        self.assertEqual(json_response['payment_date'], payment.created_at.strftime('%Y-%m-%d %H:%M'))
        self.assertEqual(json_response['payment_amount'], float(payment.amount))
        self.assertEqual(json_response['booking_status'], booking.get_booking_status_display())
        self.assertEqual(json_response['payment_status'], booking.get_payment_status_display())
        self.assertEqual(json_response['customer_notes'], 'Please check brakes.')
        self.assertEqual(json_response['entitled_refund_amount'], 125.00)
        self.assertEqual(json_response['refund_calculation_details'], mock_calculate_refund.return_value['details'])
        self.assertEqual(json_response['refund_policy_applied'], mock_calculate_refund.return_value['policy_applied'])
        self.assertEqual(json_response['refund_days_before_dropoff'], mock_calculate_refund.return_value['days_before_dropoff'])
        self.assertEqual(json_response['refund_request_status_for_booking'], 'No Refund Request Yet') # No refund request created yet

        mock_calculate_refund.assert_called_once()
        args, kwargs = mock_calculate_refund.call_args
        # Corrected: Access service_booking from kwargs, not args
        self.assertEqual(kwargs['service_booking'].id, booking.id) 
        self.assertIn('cancellation_full_payment_partial_refund_percentage', kwargs['refund_policy_snapshot'])
        self.assertEqual(kwargs['refund_policy_snapshot']['cancellation_full_payment_partial_refund_percentage'], str(Decimal('50.00')))
        self.assertIsNotNone(kwargs['cancellation_datetime'])


    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_successful_retrieval_deposit_payment_with_refund_request(self, mock_calculate_refund):
        """
        Tests successful retrieval for a deposit payment service booking, including an existing refund request.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('75.00'),
            'details': "Cancellation 6 days before drop-off. Policy: Deposit Payment Policy: Partial Refund Policy (75.00%). Calculated: 75.00 (75.00% of 100.00).",
            'policy_applied': "Deposit Payment Policy: Partial Refund Policy (75.00%)",
            'days_before_dropoff': 6,
        }

        service_profile = ServiceProfileFactory(user=self.user)
        customer_motorcycle = CustomerMotorcycleFactory()
        service_type = ServiceTypeFactory()
        payment = PaymentFactory(
            amount=Decimal('100.00'),
            status='succeeded',
            created_at=timezone.now() - timedelta(days=2),
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        dropoff_date_in_future = timezone.now().date() + timedelta(days=7) # Adjusted for 6 full days
        booking = ServiceBookingFactory(
            service_profile=service_profile,
            customer_motorcycle=customer_motorcycle,
            service_type=service_type,
            payment=payment,
            payment_option='online_deposit', # Explicitly set for this test
            payment_status='deposit_paid',
            calculated_total=Decimal('500.00'),
            amount_paid=Decimal('100.00'),
            dropoff_date=dropoff_date_in_future,
            dropoff_time=time(14, 30),
            booking_status='confirmed',
        )

        # Create a refund request for this booking
        refund_request = RefundRequestFactory(
            service_booking=booking,
            status='pending',
            amount_to_refund=Decimal('75.00'), 
            requested_at=timezone.now() - timedelta(hours=1),
        )

        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        json_response = response.json()

        self.assertEqual(json_response['entitled_refund_amount'], 75.00)
        self.assertEqual(json_response['refund_request_status_for_booking'], 'Pending Review')
        self.assertEqual(json_response['payment_amount'], float(payment.amount))
        self.assertEqual(json_response['payment_option'], 'Deposit Payment Online')

        mock_calculate_refund.assert_called_once()


    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_no_payment_object(self, mock_calculate_refund):
        """
        Tests behavior when the service booking has no associated payment object.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), # Default if no payment
            'details': "No refund policy snapshot available for this booking's payment.",
            'policy_applied': "N/A",
            'days_before_dropoff': 'N/A',
        }

        # Create a booking with no linked payment
        booking = ServiceBookingFactory(
            payment=None, # Explicitly set to None
            amount_paid=Decimal('0.00'), # No amount paid
            # Explicitly set payment_method to match expected display name for this test
            payment_option='in_store_full', # Explicitly set for this test
            payment_status='unpaid',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )

        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        self.assertEqual(json_response['payment_date'], 'N/A')
        self.assertEqual(json_response['payment_amount'], 'N/A')
        self.assertEqual(json_response['entitled_refund_amount'], 0.00)
        self.assertEqual(json_response['refund_calculation_details'], mock_calculate_refund.return_value['details'])
        self.assertEqual(json_response['refund_policy_applied'], mock_calculate_refund.return_value['policy_applied'])
        self.assertEqual(json_response['refund_days_before_dropoff'], mock_calculate_refund.return_value['days_before_dropoff'])
        self.assertEqual(json_response['refund_request_status_for_booking'], 'No Refund Request Yet')
        # Corrected assertion: use the display value as generated by the model's get_payment_method_display()
        self.assertEqual(json_response['payment_option'], booking.get_payment_option_display())

        # Ensure calculate_service_refund_amount was called with an empty snapshot
        args, kwargs = mock_calculate_refund.call_args
        self.assertEqual(kwargs['refund_policy_snapshot'], {})
        mock_calculate_refund.assert_called_once()

    def test_booking_not_found(self):
        """
        Tests response when a non-existent booking ID is provided.
        """
        # Use a large integer for a non-existent PK, as ServiceBooking uses AutoField (integer PK)
        non_existent_pk = 999999999 
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': non_existent_pk})
        response = self.client.get(url)
        # Expect 404 now that Http404 is caught first
        self.assertEqual(response.status_code, 404) 
        self.assertEqual(response.json(), {'error': 'Service Booking not found'})

    @patch('payments.utils.ajax_get_service_booking_details.get_object_or_404', side_effect=Exception("Database error"))
    def test_internal_server_error(self, mock_get_object_or_404):
        """
        Tests response when an unexpected internal error occurs.
        """
        # Use a large integer for the PK, as ServiceBooking uses AutoField (integer PK)
        booking_pk = 999999998 
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking_pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertIn('An unexpected error occurred:', response.json()['error'])

    def test_unauthenticated_access(self):
        """
        Tests that unauthenticated users cannot access the endpoint (staff_member_required).
        """
        self.client.logout() # Ensure no user is logged in
        booking = ServiceBookingFactory()
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        # login_required will redirect to login page (302)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_non_staff_user_access(self):
        """
        Tests that non-staff users cannot access the endpoint (staff_member_required).
        """
        self.client.logout()
        self.client.force_login(self.regular_user) # Login a non-staff user
        booking = ServiceBookingFactory()
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        # Now expects 403 Forbidden because @user_passes_test(..., redirect_field_name=None) is applied
        self.assertEqual(response.status_code, 403) 

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_customer_name_from_profile_name_only(self, mock_calculate_refund):
        """
        Tests customer name retrieval when user has no full name but profile has a name.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        service_profile = ServiceProfileFactory(user=None, name="Jane Smith") # No linked user
        booking = ServiceBookingFactory(
            service_profile=service_profile,
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer_name'], "Jane Smith")

    # Removed test_customer_name_n_a as service_profile cannot be None due to NOT NULL constraint.
    # The scenario where ServiceProfile.user is None is covered by test_customer_name_from_profile_name_only.

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_customer_name_from_user_full_name(self, mock_calculate_refund):
        """
        Tests customer name retrieval when user has a full name.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        user_with_full_name = UserFactory(first_name="Test", last_name="User")
        service_profile = ServiceProfileFactory(user=user_with_full_name, name="Should Be Overwritten")
        booking = ServiceBookingFactory(
            service_profile=service_profile,
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer_name'], "Test User") # Should prioritize user's full name

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_payment_details_n_a(self, mock_calculate_refund):
        """
        Tests that payment_date and payment_amount are 'N/A' when payment object is None.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        booking = ServiceBookingFactory(
            payment=None,
            amount_paid=Decimal('0.00'), # Still set amount_paid, but payment obj is None
            payment_method='in_store_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['payment_date'], 'N/A')
        self.assertEqual(json_response['payment_amount'], 'N/A')

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_motorcycle_details_n_a(self, mock_calculate_refund):
        """
        Tests that motorcycle_details are 'N/A' when customer_motorcycle is None.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        booking = ServiceBookingFactory(
            customer_motorcycle=None,
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['motorcycle_details']['year'], 'N/A')
        self.assertEqual(json_response['motorcycle_details']['brand'], 'N/A')
        self.assertEqual(json_response['motorcycle_details']['model'], 'N/A')

    # Removed test_service_type_details_n_a as service_type cannot be None due to NOT NULL constraint.

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_booking_status_display(self, mock_calculate_refund):
        """
        Tests that booking_status uses get_booking_status_display().
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        booking = ServiceBookingFactory(
            booking_status='pending', # Raw value
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['booking_status'], 'Pending') # Expected display value

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_payment_status_display(self, mock_calculate_refund):
        """
        Tests that payment_status uses get_payment_status_display().
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        booking = ServiceBookingFactory(
            payment_status='unpaid', # Raw value
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['payment_status'], 'Unpaid') # Expected display value

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_customer_notes_empty(self, mock_calculate_refund):
        """
        Tests customer_notes when it's an empty string.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        booking = ServiceBookingFactory(
            customer_notes='',
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer_notes'], '')

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_customer_notes_none(self, mock_calculate_refund):
        """
        Tests customer_notes when it's None.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_dropoff': 0
        }
        booking = ServiceBookingFactory(
            customer_notes=None,
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )
        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer_notes'], '')

    @patch('payments.utils.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_refund_policy_snapshot_none_on_payment(self, mock_calculate_refund):
        """
        Tests that if payment exists but its refund_policy_snapshot is None,
        calculate_service_refund_amount receives an empty dict.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': "No refund policy snapshot available for this booking's payment.",
            'policy_applied': "N/A",
            'days_before_dropoff': 'N/A',
        }

        payment_with_none_snapshot = PaymentFactory(
            refund_policy_snapshot=None # Explicitly set to None
        )
        booking = ServiceBookingFactory(
            payment=payment_with_none_snapshot,
            payment_method='online_full',
            dropoff_date=timezone.now().date() + timedelta(days=5),
            dropoff_time=time(10,0)
        )

        # Corrected URL name with namespace
        url = reverse('payments:api_service_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        self.assertEqual(json_response['entitled_refund_amount'], 0.00)
        self.assertEqual(json_response['refund_calculation_details'], "No refund policy snapshot available for this booking's payment.")

        # Ensure calculate_service_refund_amount was called with an empty dictionary
        args, kwargs = mock_calculate_refund.call_args
        self.assertEqual(kwargs['refund_policy_snapshot'], {})
        mock_calculate_refund.assert_called_once()
