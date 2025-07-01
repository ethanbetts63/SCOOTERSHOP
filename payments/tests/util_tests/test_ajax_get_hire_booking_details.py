                                                                 

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from datetime import time, timedelta
from unittest.mock import patch
from django.utils import timezone

                  
from payments.tests.test_helpers.model_factories import (
    HireBookingFactory, PaymentFactory, RefundRequestFactory,
    DriverProfileFactory, MotorcycleFactory, UserFactory,
    RefundPolicySettingsFactory
)


class AjaxGetHireBookingDetailsTests(TestCase):
    """
    Tests for the get_hire_booking_details_json AJAX view.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified data for all test methods.
        """
        cls.client = Client()
        cls.user = UserFactory(is_staff=True, is_active=True)                                
        cls.regular_user = UserFactory(is_staff=False, is_active=True)                 

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

    @patch('payments.utils.ajax_get_hire_booking_details.calculate_hire_refund_amount')
    def test_successful_retrieval_full_payment(self, mock_calculate_refund):
        """
        Tests successful retrieval of hire booking details for a full payment.
        """
                                            
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('150.00'),
            'details': "Cancellation 4 days before pickup. Policy: Full Payment Policy: Partial Refund (50%).",
            'policy_applied': "Full Payment Policy: Partial Refund (50%)",
            'days_before_pickup': 4,
        }

                                                      
        user_john_doe = UserFactory(first_name="John", last_name="Doe")
        driver_profile = DriverProfileFactory(user=user_john_doe, name="Fallback Name")
        motorcycle = MotorcycleFactory(brand="Harley", model="Sportster", year=2020)
        payment = PaymentFactory(
            amount=Decimal('300.00'),
            status='succeeded',
            created_at=timezone.now() - timedelta(days=1),
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        pickup_date_in_future = timezone.now().date() + timedelta(days=5)                           
        booking = HireBookingFactory(
            motorcycle=motorcycle,
            driver_profile=driver_profile,
            payment=payment,
            payment_method='online_full',
            payment_status='paid',
            grand_total=Decimal('300.00'),
            amount_paid=Decimal('300.00'),
            pickup_date=pickup_date_in_future,
            pickup_time=time(10, 0),
            return_date=pickup_date_in_future + timedelta(days=3),
            return_time=time(17, 0),
            status='confirmed',
        )

        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        self.assertEqual(json_response['id'], booking.id)
        self.assertEqual(json_response['booking_reference'], booking.booking_reference)
        self.assertEqual(json_response['customer_name'], "John Doe")
        self.assertEqual(json_response['pickup_date'], booking.pickup_date.strftime('%Y-%m-%d'))
        self.assertEqual(json_response['pickup_time'], booking.pickup_time.strftime('%H:%M'))
        self.assertEqual(json_response['return_date'], booking.return_date.strftime('%Y-%m-%d'))
        self.assertEqual(json_response['return_time'], booking.return_time.strftime('%H:%M'))
        self.assertEqual(json_response['motorcycle_year'], motorcycle.year)
        self.assertEqual(json_response['motorcycle_brand'], motorcycle.brand)
        self.assertEqual(json_response['motorcycle_model'], motorcycle.model)
        self.assertEqual(json_response['payment_method'], booking.get_payment_method_display())
        self.assertEqual(json_response['payment_date'], payment.created_at.strftime('%Y-%m-%d %H:%M'))
        self.assertEqual(json_response['payment_amount'], float(payment.amount))
        self.assertEqual(json_response['booking_status'], booking.get_status_display())
        self.assertEqual(json_response['payment_status'], booking.get_payment_status_display())
        self.assertEqual(json_response['entitled_refund_amount'], 150.00)
        self.assertEqual(json_response['refund_calculation_details'], mock_calculate_refund.return_value['details'])
        self.assertEqual(json_response['refund_policy_applied'], mock_calculate_refund.return_value['policy_applied'])
        self.assertEqual(json_response['refund_days_before_pickup'], mock_calculate_refund.return_value['days_before_pickup'])
        self.assertEqual(json_response['refund_request_status_for_booking'], 'No Refund Request Yet')

        mock_calculate_refund.assert_called_once()
        args, kwargs = mock_calculate_refund.call_args
        self.assertEqual(kwargs['booking'].id, booking.id)
        self.assertIn('cancellation_full_payment_partial_refund_percentage', kwargs['refund_policy_snapshot'])
        self.assertIsNotNone(kwargs['cancellation_datetime'])

    @patch('payments.utils.ajax_get_hire_booking_details.calculate_hire_refund_amount')
    def test_successful_retrieval_deposit_payment_with_refund_request(self, mock_calculate_refund):
        """
        Tests successful retrieval for a deposit payment hire booking, including an existing refund request.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('75.00'),
            'details': "Cancellation 6 days before pickup. Policy: Deposit Payment Policy: Partial Refund (75%).",
            'policy_applied': "Deposit Payment Policy: Partial Refund (75%)",
            'days_before_pickup': 6,
        }

        driver_profile = DriverProfileFactory(user=self.user)
        motorcycle = MotorcycleFactory()
        payment = PaymentFactory(
            amount=Decimal('100.00'),
            status='succeeded',
            created_at=timezone.now() - timedelta(days=2),
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        pickup_date_in_future = timezone.now().date() + timedelta(days=7)                           
        booking = HireBookingFactory(
            motorcycle=motorcycle,
            driver_profile=driver_profile,
            payment=payment,
            payment_method='online_deposit',                 
            payment_status='deposit_paid',
            grand_total=Decimal('500.00'),
            amount_paid=Decimal('100.00'),
            pickup_date=pickup_date_in_future,
            pickup_time=time(14, 30),
            return_date=pickup_date_in_future + timedelta(days=2),
            return_time=time(10, 0),
            status='confirmed',
        )

                                                  
        refund_request = RefundRequestFactory(
            hire_booking=booking,
            status='pending',
            amount_to_refund=Decimal('75.00'),
            requested_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        json_response = response.json()

        self.assertEqual(json_response['entitled_refund_amount'], 75.00)
        self.assertEqual(json_response['refund_request_status_for_booking'], 'Pending Review')
        self.assertEqual(json_response['payment_amount'], float(payment.amount))
        self.assertEqual(json_response['payment_method'], 'Deposit Payment Online')

        mock_calculate_refund.assert_called_once()

    @patch('payments.utils.ajax_get_hire_booking_details.calculate_hire_refund_amount')
    def test_no_payment_object(self, mock_calculate_refund):
        """
        Tests behavior when the hire booking has no associated payment object.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': "No refund policy snapshot available for this booking's payment.",
            'policy_applied': "N/A",
            'days_before_pickup': 'N/A',
        }

                                                                                                     
        booking = HireBookingFactory(
            payment=None,
            amount_paid=Decimal('0.00'),
            payment_method='in_store_full',                 
            payment_status='unpaid',
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10, 0),
            return_date=timezone.now().date() + timedelta(days=6),
            return_time=time(17,0)
        )

        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        self.assertEqual(json_response['payment_date'], 'N/A')
        self.assertEqual(json_response['payment_amount'], 'N/A')
        self.assertEqual(json_response['entitled_refund_amount'], 0.00)
        self.assertEqual(json_response['refund_calculation_details'], mock_calculate_refund.return_value['details'])
        self.assertEqual(json_response['refund_policy_applied'], mock_calculate_refund.return_value['policy_applied'])
        self.assertEqual(json_response['refund_days_before_pickup'], mock_calculate_refund.return_value['days_before_pickup'])
        self.assertEqual(json_response['refund_request_status_for_booking'], 'No Refund Request Yet')
        self.assertEqual(json_response['payment_method'], booking.get_payment_method_display())

                                                                               
        args, kwargs = mock_calculate_refund.call_args
        self.assertEqual(kwargs['refund_policy_snapshot'], {})
        mock_calculate_refund.assert_called_once()

    def test_booking_not_found(self):
        """
        Tests response when a non-existent booking ID is provided.
        """
        non_existent_pk = 999999999
        url = reverse('payments:api_hire_booking_details', kwargs={'pk': non_existent_pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Hire Booking not found'})

    @patch('payments.utils.ajax_get_hire_booking_details.get_object_or_404', side_effect=Exception("Database error"))
    def test_internal_server_error(self, mock_get_object_or_404):
        """
        Tests response when an unexpected internal error occurs.
        """
        booking_pk = 999999998
        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking_pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertIn('An unexpected error occurred:', response.json()['error'])

    def test_unauthenticated_access(self):
        """
        Tests that unauthenticated users cannot access the endpoint.
        """
        self.client.logout()
        booking = HireBookingFactory()
        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_non_staff_user_access(self):
        """
        Tests that non-staff users cannot access the endpoint (should result in 403 Forbidden).
        """
        self.client.logout()
        self.client.force_login(self.regular_user)
        booking = HireBookingFactory()
        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)                       

    @patch('payments.utils.ajax_get_hire_booking_details.calculate_hire_refund_amount')
    def test_customer_name_from_profile_name_only(self, mock_calculate_refund):
        """
        Tests customer name retrieval when driver profile has a name but no linked user.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_pickup': 0
        }
        driver_profile = DriverProfileFactory(user=None, name="Jane Smith")
        booking = HireBookingFactory(
            driver_profile=driver_profile,
            payment_method='online_full',
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=6),
            return_time=time(17,0)
        )
        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer_name'], "Jane Smith")

    @patch('payments.utils.ajax_get_hire_booking_details.calculate_hire_refund_amount')
    def test_customer_name_from_user_full_name(self, mock_calculate_refund):
        """
        Tests customer name retrieval when driver profile is linked to a user with a full name.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'), 'details': '', 'policy_applied': '', 'days_before_pickup': 0
        }
        user_test = UserFactory(first_name="Test", last_name="User")
        driver_profile = DriverProfileFactory(user=user_test, name="Should Be Overwritten")
        booking = HireBookingFactory(
            driver_profile=driver_profile,
            payment_method='online_full',
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=6),
            return_time=time(17,0)
        )
        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer_name'], "Test User")

                                                                            

    @patch('payments.utils.ajax_get_hire_booking_details.calculate_hire_refund_amount')
    def test_refund_policy_snapshot_none_on_payment(self, mock_calculate_refund):
        """
        Tests that if payment exists but its refund_policy_snapshot is None,
        calculate_hire_refund_amount receives an empty dict.
        """
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': "No refund policy snapshot available for this booking's payment.",
            'policy_applied': "N/A",
            'days_before_pickup': 'N/A',
        }

        payment_with_none_snapshot = PaymentFactory(
            refund_policy_snapshot=None                         
        )
        booking = HireBookingFactory(
            payment=payment_with_none_snapshot,
            payment_method='online_full',
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=6),
            return_time=time(17,0)
        )

        url = reverse('payments:api_hire_booking_details', kwargs={'pk': booking.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        self.assertEqual(json_response['entitled_refund_amount'], 0.00)
        self.assertEqual(json_response['refund_calculation_details'], "No refund policy snapshot available for this booking's payment.")

                                                                                 
        args, kwargs = mock_calculate_refund.call_args
        self.assertEqual(kwargs['refund_policy_snapshot'], {})
        mock_calculate_refund.assert_called_once()
