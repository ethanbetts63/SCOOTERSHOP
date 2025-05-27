# hire/tests/view_tests/test_step6_hire_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from decimal import Decimal
import datetime
import uuid
from unittest.mock import patch, MagicMock
import json
import stripe # Import stripe to catch its errors

# Import models
from hire.models import TempHireBooking, HireBooking
from payments.models import Payment
from dashboard.models import HireSettings

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_temp_hire_booking,
    create_driver_profile,
)

class PaymentDetailsViewTest(TestCase):
    """
    Tests for the PaymentDetailsView (Step 6 of the hire booking process).
    """

    def setUp(self):
        """
        Set up common URLs, HireSettings, Motorcycle, and DriverProfile.
        """
        self.client = Client()
        self.step6_url = reverse('hire:step6_payment_details')
        self.step2_url = reverse('hire:step2_choose_bike')
        self.step5_url = reverse('hire:step5_summary_payment_options')
        self.step7_url_base = reverse('hire:step7_confirmation')
        # self.payment_failed_url_base = reverse('hire:payment_failed') # Removed as it's no longer needed

        # Ensure HireSettings exists and payment options are enabled for testing
        self.hire_settings = create_hire_settings(
            deposit_enabled=True,
            deposit_percentage=Decimal('20.00'),
            enable_online_full_payment=True,
            enable_online_deposit_payment=True,
            enable_in_store_full_payment=True, # Though not used in step6, keep consistent
            hire_pricing_strategy='24_hour_customer_friendly'
        )

        # Create a motorcycle for default bookings
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00'),
            is_available=True,
            engine_size=125
        )
        # Create a driver profile to associate with bookings
        self.driver_profile = create_driver_profile()

        # Common booking dates/times
        self.pickup_date = datetime.date.today() + datetime.timedelta(days=1)
        self.return_date = self.pickup_date + datetime.timedelta(days=2)
        self.pickup_time = datetime.time(9, 0)
        self.return_time = datetime.time(17, 0)

    def _create_and_set_temp_booking_in_session(self, motorcycle=None, pickup_date=None, pickup_time=None, return_date=None, return_time=None, has_motorcycle_license=True, driver_profile=None, payment_option='online_full', grand_total=Decimal('300.00'), deposit_amount=Decimal('60.00')):
        """
        Helper to create a TempHireBooking and set its ID/UUID in the session.
        Ensures valid dates/times and license for availability checks.
        Adds payment_option, grand_total, and deposit_amount for Step 6 tests.
        """
        if motorcycle is None:
            motorcycle = self.motorcycle
        if pickup_date is None:
            pickup_date = self.pickup_date
        if pickup_time is None:
            pickup_time = self.pickup_time
        if return_date is None:
            return_date = self.return_date
        if return_time is None:
            return_time = self.return_time
        if driver_profile is None:
            driver_profile = self.driver_profile

        temp_booking = create_temp_hire_booking(
            motorcycle=motorcycle,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=return_date,
            return_time=return_time,
            total_hire_price=Decimal('250.00'),
            grand_total=grand_total,
            deposit_amount=deposit_amount,
            has_motorcycle_license=has_motorcycle_license,
            driver_profile=driver_profile,
            payment_option=payment_option, # Set payment option for the test
            currency='AUD' # Default currency for tests
        )
        session = self.client.session
        session['temp_booking_id'] = temp_booking.id
        session['temp_booking_uuid'] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    # --- GET Request Tests ---

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_success_online_full_payment(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request with valid temp_booking for online_full payment.
        Should create a Stripe PaymentIntent and render the payment page.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')

        # Mock Stripe PaymentIntent.create
        mock_stripe_create.return_value = MagicMock(
            id='pi_test_full',
            client_secret='cs_test_full',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )
        # Mock Stripe PaymentIntent.retrieve (should not be called on first GET for new PI)
        mock_stripe_retrieve.side_effect = stripe.error.InvalidRequestError("No such payment_intent", "id")

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertIn('client_secret', response.context)
        self.assertEqual(response.context['client_secret'], 'cs_test_full')
        self.assertEqual(response.context['amount'], temp_booking.grand_total)
        self.assertEqual(response.context['currency'], 'AUD')
        self.assertEqual(response.context['temp_booking'].id, temp_booking.id)
        self.assertIn('stripe_publishable_key', response.context)

        # Verify a Payment object was created in the DB
        payment = Payment.objects.get(temp_hire_booking=temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test_full')
        self.assertEqual(payment.amount, temp_booking.grand_total)
        self.assertEqual(payment.status, 'requires_payment_method')

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_success_online_deposit_payment(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request with valid temp_booking for online_deposit payment.
        Should create a Stripe PaymentIntent for the deposit amount.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_deposit')

        # Mock Stripe PaymentIntent.create
        mock_stripe_create.return_value = MagicMock(
            id='pi_test_deposit',
            client_secret='cs_test_deposit',
            amount=int(temp_booking.deposit_amount * 100),
            currency='aud',
            status='requires_payment_method'
        )
        mock_stripe_retrieve.side_effect = stripe.error.InvalidRequestError("No such payment_intent", "id")


        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertIn('client_secret', response.context)
        self.assertEqual(response.context['client_secret'], 'cs_test_deposit')
        self.assertEqual(response.context['amount'], temp_booking.deposit_amount)
        self.assertEqual(response.context['currency'], 'AUD')
        self.assertEqual(response.context['temp_booking'].id, temp_booking.id)

        # Verify a Payment object was created in the DB
        payment = Payment.objects.get(temp_hire_booking=temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test_deposit')
        self.assertEqual(payment.amount, temp_booking.deposit_amount)
        self.assertEqual(payment.status, 'requires_payment_method')


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_no_temp_booking_id_in_session(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request without temp_booking_id in session.
        Should redirect to step 2.
        """
        # Ensure no temp_booking_id in session
        session = self.client.session
        if 'temp_booking_id' in session:
            del session['temp_booking_id']
        session.save()

        response = self.client.get(self.step6_url)
        self.assertRedirects(response, self.step2_url)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_invalid_temp_booking_id_in_session(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request with an invalid temp_booking_id in session.
        Should redirect to step 2.
        """
        session = self.client.session
        session['temp_booking_id'] = 99999 # Non-existent ID
        session.save()

        response = self.client.get(self.step6_url)
        self.assertRedirects(response, self.step2_url)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_invalid_payment_option(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when temp_booking has an invalid payment_option (e.g., 'in_store_full').
        Should redirect to step 5.
        """
        self._create_and_set_temp_booking_in_session(payment_option='in_store_full') # Invalid for step 6

        response = self.client.get(self.step6_url)
        self.assertRedirects(response, self.step5_url)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_existing_payment_intent_reused(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing Payment object with a valid PI exists.
        Should retrieve and reuse the existing PaymentIntent.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')
        # Create an existing Payment object
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_existing_test',
            amount=temp_booking.grand_total,
            currency='AUD',
            status='requires_payment_method',
            description='Existing booking payment'
        )

        # Mock Stripe PaymentIntent.retrieve to return the existing PI
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_existing_test',
            client_secret='cs_existing_test',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )
        # Ensure create is not called
        mock_stripe_create.assert_not_called()

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertEqual(response.context['client_secret'], 'cs_existing_test')
        self.assertEqual(response.context['amount'], temp_booking.grand_total)

        mock_stripe_retrieve.assert_called_once_with('pi_existing_test')
        mock_stripe_create.assert_not_called() # Should not create a new one

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_request_existing_payment_intent_modified_amount(self, mock_stripe_modify, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing Payment object exists but amount changed.
        Should modify the existing PaymentIntent.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full', grand_total=Decimal('300.00'))
        # Create an existing Payment object with a different amount
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_existing_test_modify',
            amount=Decimal('200.00'), # Old amount
            currency='AUD',
            status='requires_payment_method',
            description='Existing booking payment'
        )

        # Mock Stripe PaymentIntent.retrieve to return the existing PI (with old amount)
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_existing_test_modify',
            client_secret='cs_existing_test_modify',
            amount=int(Decimal('200.00') * 100), # Old amount in cents
            currency='aud',
            status='requires_payment_method'
        )
        # Mock Stripe PaymentIntent.modify to return the updated PI
        mock_stripe_modify.return_value = MagicMock(
            id='pi_existing_test_modify',
            client_secret='cs_existing_test_modify',
            amount=int(temp_booking.grand_total * 100), # New amount in cents
            currency='aud',
            status='requires_payment_method'
        )

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertEqual(response.context['client_secret'], 'cs_existing_test_modify')
        self.assertEqual(response.context['amount'], temp_booking.grand_total)

        mock_stripe_retrieve.assert_called_once_with('pi_existing_test_modify')
        mock_stripe_modify.assert_called_once_with(
            'pi_existing_test_modify',
            amount=int(temp_booking.grand_total * 100),
            currency='AUD',
            description=f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}",
            metadata={
                'temp_booking_id': str(temp_booking.id),
                'user_id': str(self.driver_profile.id),
                'booking_type': 'hire_booking',
            }
        )
        mock_stripe_create.assert_not_called() # Should not create a new one

        # Verify local Payment object was updated
        existing_payment.refresh_from_db()
        self.assertEqual(existing_payment.amount, temp_booking.grand_total)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_existing_payment_intent_create_new_if_unmodifiable(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing Payment object exists but its PI is unmodifiable.
        Should create a new PaymentIntent and update the existing Payment object.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_unmodifiable_test',
            amount=temp_booking.grand_total,
            currency='AUD',
            status='succeeded', # Unmodifiable status
            description='Existing booking payment'
        )

        # Mock Stripe PaymentIntent.retrieve to return the unmodifiable PI
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_unmodifiable_test',
            client_secret='cs_unmodifiable_test',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='succeeded'
        )
        # Mock Stripe PaymentIntent.create to return a new PI
        mock_stripe_create.return_value = MagicMock(
            id='pi_new_test',
            client_secret='cs_new_test',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertEqual(response.context['client_secret'], 'cs_new_test') # Should use the new PI's secret

        mock_stripe_retrieve.assert_called_once_with('pi_unmodifiable_test')
        mock_stripe_create.assert_called_once() # Should create a new one

        # Verify local Payment object was updated with the new PI ID
        existing_payment.refresh_from_db()
        self.assertEqual(existing_payment.stripe_payment_intent_id, 'pi_new_test')


    # --- POST Request Tests ---

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_request_payment_succeeded(self, mock_stripe_retrieve):
        """
        Test POST request when Stripe reports payment succeeded.
        Should return success JSON and redirect URL to step 7.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_succeeded',
            amount=temp_booking.grand_total,
            currency='AUD',
            status='requires_confirmation',
            description='Test payment'
        )

        # Mock Stripe PaymentIntent.retrieve to return succeeded status
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_succeeded',
            status='succeeded'
        )

        post_data = {'payment_intent_id': 'pi_succeeded'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        self.assertIn(self.step7_url_base, json_response['redirect_url'])
        self.assertIn('payment_intent_id=pi_succeeded', json_response['redirect_url'])

        # Verify Payment object status (should not be updated by POST, webhook does it)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'requires_confirmation') # Status should NOT change here, webhook handles it

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_request_payment_requires_action(self, mock_stripe_retrieve):
        """
        Test POST request when Stripe reports payment requires action.
        Should return requires_action JSON without a redirect URL.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_requires_action',
            amount=temp_booking.grand_total,
            currency='AUD',
            status='requires_payment_method',
            description='Test payment'
        )

        # Mock Stripe PaymentIntent.retrieve to return requires_action status
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_requires_action',
            status='requires_action'
        )

        post_data = {'payment_intent_id': 'pi_requires_action'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'requires_action')
        # Assert redirect_url is NOT present
        self.assertNotIn('redirect_url', json_response)

        # Verify Payment object status is updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'requires_action')

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_request_payment_failed(self, mock_stripe_retrieve):
        """
        Test POST request when Stripe reports payment failed.
        Should return failed JSON without a redirect URL.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_failed',
            amount=temp_booking.grand_total,
            currency='AUD',
            status='requires_confirmation',
            description='Test payment'
        )

        # Mock Stripe PaymentIntent.retrieve to return failed status
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_failed',
            status='failed'
        )

        post_data = {'payment_intent_id': 'pi_failed'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'failed')
        # Assert redirect_url is NOT present
        self.assertNotIn('redirect_url', json_response)

        # Verify Payment object status is updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')

    def test_post_request_invalid_json(self):
        """
        Test POST request with invalid JSON in the body.
        Should return 400 error.
        """
        response = self.client.post(self.step6_url, "this is not json", content_type='application/json')
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('error', json_response)

    def test_post_request_missing_payment_intent_id(self):
        """
        Test POST request with valid JSON but missing payment_intent_id.
        Should return 400 error.
        """
        post_data = {'some_other_field': 'value'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('error', json_response)

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_request_stripe_api_error(self, mock_stripe_retrieve):
        """
        Test POST request when Stripe API raises an error during retrieve.
        Should return 500 error.
        """
        mock_stripe_retrieve.side_effect = stripe.error.StripeError("Stripe API is down!")

        post_data = {'payment_intent_id': 'pi_any_id'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')
        self.assertEqual(response.status_code, 500)
        json_response = response.json()
        self.assertIn('error', json_response)
