# inventory/tests/test_views/test_step3_payment_view.py

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
import json
from decimal import Decimal
from unittest import mock # Using 'mock' for patching
import stripe # Import the actual stripe library to access its error classes

from inventory.models import TempSalesBooking, InventorySettings
from payments.models import Payment # Ensure this is imported for PaymentFactory and assertions

from ...test_helpers.model_factories import (
    TempSalesBookingFactory,
    InventorySettingsFactory,
    MotorcycleFactory,
    SalesProfileFactory,
    PaymentFactory,
)

# Mock the stripe library globally for all tests in this file
# This prevents actual API calls to Stripe.
# We need to patch 'stripe' where it's imported in the Step3PaymentView.
# The path is 'inventory.views.user_views.step3_payment_view.stripe'
stripe_mock = mock.MagicMock()
stripe_mock.error = mock.MagicMock() # Create a mock for the error module
stripe_mock.error.StripeError = stripe.error.StripeError
stripe_mock.error.CardError = stripe.error.CardError
stripe_mock.error.RateLimitError = stripe.error.RateLimitError
stripe_mock.error.InvalidRequestError = stripe.error.InvalidRequestError
stripe_mock.error.AuthenticationError = stripe.error.AuthenticationError
stripe_mock.error.APIConnectionError = stripe.error.APIConnectionError


@mock.patch('inventory.views.user_views.step3_payment_view.stripe', stripe_mock)
class Step3PaymentViewTest(TestCase):
    """
    Tests for the Step3PaymentView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()
        cls.url = reverse('inventory:step3_payment')

        # Ensure a singleton InventorySettings instance exists
        cls.inventory_settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('100.00'),
            currency_code='AUD',
        )

        # Create dummy motorcycle and sales profile
        cls.motorcycle = MotorcycleFactory(price=Decimal('10000.00'))
        cls.sales_profile = SalesProfileFactory()

    def setUp(self):
        """
        Set up before each test method.
        Ensure a clean state and a valid temporary booking for most tests.
        """
        # Clear existing TempSalesBookings and Payments to ensure test isolation
        TempSalesBooking.objects.all().delete()
        Payment.objects.all().delete()

        # Reset the mock before each test to ensure isolation
        stripe_mock.reset_mock()
        # Mock stripe.PaymentIntent.retrieve for POST requests
        self.mock_stripe_retrieve = stripe_mock.PaymentIntent.retrieve
        # Mock stripe.PaymentIntent.create for GET requests within create_or_update_sales_payment_intent
        # This will be patched directly on the utility function where it's used.

        # Create a valid temporary booking and set it in the session for most tests
        # This ensures the dispatch method passes for tests that target GET/POST logic
        self.temp_booking = self._create_temp_booking_in_session(
            self.client,
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=self.inventory_settings.deposit_amount,
            deposit_required_for_flow=True, # Critical for proceeding to payment logic
            booking_status='pending_confirmation',
        )

    def _create_temp_booking_in_session(self, client, **kwargs):
        """
        Helper to create a TempSalesBooking and set its session_uuid (as string) in the session.
        Allows overriding temp_booking fields via kwargs.
        """
        temp_booking = TempSalesBookingFactory(**kwargs)
        session = client.session
        session['temp_sales_booking_uuid'] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    # --- Dispatch Method Tests (Session and Initial Checks) ---

    def test_dispatch_no_temp_booking_uuid_in_session(self):
        """
        Test dispatch when 'temp_sales_booking_uuid' is not in session.
        Should redirect to 'inventory:used' with an error message.
        """
        self.client.session.pop('temp_sales_booking_uuid', None) # Clear the UUID from session
        self.client.session.save()

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:used'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired or is invalid." in str(m) for m in messages_list))

    def test_dispatch_invalid_temp_booking_uuid(self):
        """
        Test dispatch with an invalid 'temp_sales_booking_uuid' in session.
        Should redirect to 'inventory:used' with an error message.
        """
        session = self.client.session
        session['temp_sales_booking_uuid'] = 'a2b3c4d5-e6f7-8901-2345-67890abcdef0' # Invalid UUID
        session.save()

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:used'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages_list))

    def test_dispatch_no_motorcycle_in_temp_booking(self):
        """
        Test dispatch when temp_booking has no associated motorcycle.
        Should redirect to 'inventory:used' with an error message.
        """
        # Create a temp booking specifically for this test with no motorcycle
        temp_booking_no_mc = self._create_temp_booking_in_session(self.client, motorcycle=None)
        
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:used'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Please select a motorcycle first." in str(m) for m in messages_list))

    def test_dispatch_no_sales_profile_in_temp_booking(self):
        """
        Test dispatch when temp_booking has no associated sales_profile.
        Should redirect to 'inventory:step2_booking_details_and_appointment' with an error message.
        """
        # Create a temp booking specifically for this test with no sales_profile
        temp_booking_no_profile = self._create_temp_booking_in_session(self.client, sales_profile=None)

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Please provide your contact details first." in str(m) for m in messages_list))

    def test_dispatch_no_inventory_settings(self):
        """
        Test dispatch when no InventorySettings exist.
        Should redirect to 'inventory:used' with an error message.
        """
        # Ensure that setup() created a temp booking for the session, then delete settings
        InventorySettings.objects.all().delete() 
        self.assertFalse(InventorySettings.objects.exists()) # Verify deletion

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:used'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Inventory settings are not configured. Please contact support." in str(m) for m in messages_list))

        # Recreate settings for subsequent tests in other methods
        self.inventory_settings = InventorySettingsFactory(pk=1)

    def test_dispatch_not_deposit_required_for_flow(self):
        """
        Test dispatch when deposit_required_for_flow is False.
        Should redirect to step4_confirmation with a warning.
        """
        # Create a temp booking specifically for this test with deposit_required_for_flow=False
        temp_booking_no_deposit = self._create_temp_booking_in_session(self.client, deposit_required_for_flow=False)
        
        response = self.client.get(self.url, follow=True)
        expected_redirect_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={temp_booking_no_deposit.stripe_payment_intent_id if temp_booking_no_deposit.stripe_payment_intent_id else ""}'
        self.assertRedirects(response, expected_redirect_url)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Payment is not required for this type of booking. Redirecting to confirmation." in str(m) for m in messages_list))

    # --- GET Request Tests ---

    @mock.patch('inventory.utils.create_update_sales_payment_intent.create_or_update_sales_payment_intent')
    def test_get_invalid_amount_to_pay(self, mock_create_intent):
        """
        Test GET request when amount_to_pay is invalid (None or <= 0).
        Should redirect to step2_booking_details_and_appointment.
        """
        # Overwrite the temp_booking created in setUp for this specific test
        self.temp_booking = self._create_temp_booking_in_session(self.client, amount_paid=None)
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("The amount to pay is invalid. Please review your booking details." in str(m) for m in messages_list))
        mock_create_intent.assert_not_called()

        self.temp_booking = self._create_temp_booking_in_session(self.client, amount_paid=Decimal('0.00'))
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("The amount to pay is invalid. Please review your booking details." in str(m) for m in messages_list))
        mock_create_intent.assert_not_called()

    @mock.patch('inventory.utils.create_update_sales_payment_intent.create_or_update_sales_payment_intent')
    def test_get_create_payment_intent_success(self, mock_create_intent):
        """
        Test successful GET request, ensuring client_secret and other context are passed.
        """
        # Configure the mock PaymentIntent object
        mock_intent = mock.MagicMock()
        mock_intent.client_secret = 'test_client_secret_123'
        mock_intent.id = 'pi_test_123'
        # Pass a mock payment object or allow it to be created
        mock_payment_obj = PaymentFactory(stripe_payment_intent_id=mock_intent.id, temp_sales_booking=self.temp_booking)
        mock_create_intent.return_value = (mock_intent, mock_payment_obj)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/step3_payment.html')

        context = response.context
        self.assertEqual(context['client_secret'], 'test_client_secret_123')
        self.assertEqual(context['amount'], Decimal('100.00'))
        self.assertEqual(context['currency'], 'AUD')
        self.assertEqual(context['temp_booking'], self.temp_booking)
        self.assertIn('stripe_publishable_key', context) # Check presence, actual value depends on settings
        self.assertEqual(context['amount_remaining'], self.motorcycle.price - Decimal('100.00'))

        mock_create_intent.assert_called_once_with(
            temp_booking=self.temp_booking,
            sales_profile=self.temp_booking.sales_profile,
            amount_to_pay=Decimal('100.00'),
            currency='AUD',
            existing_payment_obj=None # No existing payment by default in setUp
        )

    @mock.patch('inventory.utils.create_update_sales_payment_intent.create_or_update_sales_payment_intent')
    def test_get_create_payment_intent_stripe_error(self, mock_create_intent):
        """
        Test GET request when create_or_update_sales_payment_intent raises a StripeError.
        """
        mock_create_intent.side_effect = stripe_mock.error.CardError("Card declined", param='card', code='card_declined')
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Payment system error: Card declined. Please try again later." in str(m) for m in messages_list))

    @mock.patch('inventory.utils.create_update_sales_payment_intent.create_or_update_sales_payment_intent')
    def test_get_create_payment_intent_generic_exception(self, mock_create_intent):
        """
        Test GET request when create_or_update_sales_payment_intent raises a generic exception.
        """
        mock_create_intent.side_effect = Exception("Something went wrong.")
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("An unexpected error occurred during payment setup. Please try again." in str(m) for m in messages_list))

    @mock.patch('inventory.utils.create_update_sales_payment_intent.create_or_update_sales_payment_intent')
    def test_get_create_payment_intent_returns_none(self, mock_create_intent):
        """
        Test GET request when create_or_update_sales_payment_intent returns None for intent.
        """
        mock_create_intent.return_value = (None, None)
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any("Could not set up payment. Please try again." in str(m) for m in messages_list))

    # --- POST Request Tests ---

    def test_post_invalid_json(self):
        """
        Test POST request with invalid JSON payload.
        """
        # No temp_booking needs to be active for this specific test case,
        # as it tests the JSON decoding *before* dispatch's session checks.
        self.client.session.pop('temp_sales_booking_uuid', None)
        self.client.session.save()

        response = self.client.post(self.url, data='not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON format in request body', json.loads(response.content)['error'])

    def test_post_missing_payment_intent_id(self):
        """
        Test POST request with missing 'payment_intent_id' in JSON payload.
        """
        # No temp_booking needs to be active for this specific test case,
        # as it tests the JSON parsing *before* dispatch's session checks.
        self.client.session.pop('temp_sales_booking_uuid', None)
        self.client.session.save()

        response = self.client.post(self.url, data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Payment Intent ID is required in the request', json.loads(response.content)['error'])

    def test_post_payment_succeeded(self):
        """
        Test POST request when Stripe PaymentIntent status is 'succeeded'.
        Should return success JSON response and redirect URL.
        """
        mock_intent = mock.MagicMock(id='pi_succeeded_123', status='succeeded')
        self.mock_stripe_retrieve.return_value = mock_intent

        # Create a payment object linked to the temp booking and the mocked payment intent
        # This simulates an existing payment that is now being checked for status
        payment_obj = PaymentFactory(
            temp_sales_booking=self.temp_booking,
            stripe_payment_intent_id='pi_succeeded_123',
            status='requires_action' # Initial status before POST
        )

        response = self.client.post(
            self.url,
            data=json.dumps({'payment_intent_id': 'pi_succeeded_123'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertEqual(json_response['status'], 'success')
        self.assertEqual(json_response['message'], 'Payment processed successfully. Your booking is being finalized.')
        self.assertEqual(json_response['redirect_url'], reverse('inventory:step4_confirmation') + '?payment_intent_id=pi_succeeded_123')
        self.mock_stripe_retrieve.assert_called_once_with('pi_succeeded_123')

        # Verify payment status is updated if it was different
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'succeeded') # The view updates the status on success

    def test_post_payment_requires_action(self):
        """
        Test POST request when Stripe PaymentIntent status requires action.
        """
        mock_intent = mock.MagicMock(id='pi_action_123', status='requires_action')
        self.mock_stripe_retrieve.return_value = mock_intent

        payment_obj = PaymentFactory(
            temp_sales_booking=self.temp_booking,
            stripe_payment_intent_id='pi_action_123',
            status='unpaid' # Initial status before POST
        )

        response = self.client.post(
            self.url,
            data=json.dumps({'payment_intent_id': 'pi_action_123'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertEqual(json_response['status'], 'requires_action')
        self.assertIn('Payment requires further action', json_response['message'])
        self.mock_stripe_retrieve.assert_called_once_with('pi_action_123')

        # Verify payment status is updated
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'requires_action')

    def test_post_payment_failed_or_unexpected(self):
        """
        Test POST request when Stripe PaymentIntent status is 'canceled' (or other non-success/non-action).
        """
        mock_intent = mock.MagicMock(id='pi_failed_123', status='canceled')
        self.mock_stripe_retrieve.return_value = mock_intent

        payment_obj = PaymentFactory(
            temp_sales_booking=self.temp_booking,
            stripe_payment_intent_id='pi_failed_123',
            status='unpaid' # Initial status before POST
        )

        response = self.client.post(
            self.url,
            data=json.dumps({'payment_intent_id': 'pi_failed_123'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertEqual(json_response['status'], 'failed')
        self.assertIn('Payment failed or an unexpected status occurred', json_response['message'])
        self.mock_stripe_retrieve.assert_called_once_with('pi_failed_123')

        # Verify payment status is updated
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'canceled')


    def test_post_stripe_error_during_retrieve(self):
        """
        Test POST request when StripeError occurs during PaymentIntent retrieve.
        """
        # Ensure a temp_booking exists in the session so dispatch passes
        temp_booking_for_error = self._create_temp_booking_in_session(self.client)

        self.mock_stripe_retrieve.side_effect = stripe_mock.error.StripeError("Stripe API error.")

        response = self.client.post(
            self.url,
            data=json.dumps({'payment_intent_id': 'pi_error_123'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn('Stripe API error.', json.loads(response.content)['error'])
        self.mock_stripe_retrieve.assert_called_once_with('pi_error_123')

    def test_post_generic_exception(self):
        """
        Test POST request when a generic exception occurs.
        """
        # Ensure a temp_booking exists in the session so dispatch passes
        temp_booking_for_generic_error = self._create_temp_booking_in_session(self.client)

        self.mock_stripe_retrieve.side_effect = Exception("Internal server issue.")

        response = self.client.post(
            self.url,
            data=json.dumps({'payment_intent_id': 'pi_generic_error'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn('An internal server error occurred', json.loads(response.content)['error'])
        self.mock_stripe_retrieve.assert_called_once_with('pi_generic_error')

