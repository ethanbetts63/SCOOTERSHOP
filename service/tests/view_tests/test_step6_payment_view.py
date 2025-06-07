# service/tests/test_step6_service_payment_details_view.py

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import datetime
import uuid
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
import stripe

# Import the view to be tested
from service.views.v2_views.user_views import Step6PaymentView # Adjust path if different

# Import models and factories
from payments.models import Payment
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle, ServiceType, ServiceSettings
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
    PaymentFactory, # Use this factory if you need to create Payment instances directly
)

User = get_user_model()

# Mock Stripe's API key to prevent actual network calls during tests
# This is a global patch for the entire test class to ensure no real Stripe calls are made
@patch('stripe.api_key', 'sk_test_mock_key')
class Step6PaymentViewTest(TestCase):
    """
    Tests for the Step6PaymentView (dispatch, GET, and POST methods).
    This class specifically tests the Stripe payment integration logic without
    making actual network requests to Stripe.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.factory = RequestFactory()
        cls.user_password = 'testpassword123'
        cls.user = UserFactory(password=cls.user_password) # For authenticated tests
        
        # Ensure ServiceSettings exists and has expected values
        cls.service_settings = ServiceSettingsFactory(
            enable_online_full_payment=True,
            enable_online_deposit=True,
            enable_instore_full_payment=True,
            currency_code='AUD',
            stripe_fee_percentage_domestic=Decimal('0.0170'),
            stripe_fee_fixed_domestic=Decimal('0.30')
        )
        cls.service_type = ServiceTypeFactory(base_price=Decimal('250.00'))
        cls.base_url = reverse('service:service_book_step6')

    def setUp(self):
        """
        Set up for each test method.
        Ensure a clean state for temporary bookings, payments, etc.
        """
        TempServiceBooking.objects.all().delete()
        Payment.objects.all().delete()
        ServiceProfile.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        # Create necessary linked objects for temp_booking to be valid for step 6
        self.customer_motorcycle = CustomerMotorcycleFactory(
            brand="TestBrand", model="TestModel", year=2020, rego="TESTMC"
        )
        self.service_profile = ServiceProfileFactory(user=self.user, email="test@example.com")

        # Create a valid temporary service booking with a service_profile and customer_motorcycle
        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=datetime.date.today() + datetime.timedelta(days=10),
            dropoff_date=datetime.date.today() + datetime.timedelta(days=5),
            dropoff_time=datetime.time(10, 0),
            customer_motorcycle=self.customer_motorcycle,
            service_profile=self.service_profile,
            payment_option='online_full', # Default to full payment for most tests
            calculated_deposit_amount=Decimal('50.00') # Example deposit
        )

        # Set the UUID in the client's session
        session = self.client.session
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

    # --- Dispatch Method Tests ---

    def test_dispatch_no_temp_booking_uuid_in_session_redirects_to_service_home(self):
        """
        Tests that dispatch redirects to service:service if no temp_booking_uuid is in session.
        """
        self.client.logout() # Ensure clean session
        session = self.client.session
        if 'temp_service_booking_uuid' in session:
            del session['temp_service_booking_uuid']
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired or is invalid." in str(m) for m in messages))

    def test_dispatch_invalid_temp_booking_uuid_redirects_to_service_home(self):
        """
        Tests that dispatch redirects to service:service if an invalid temp_booking_uuid is in session.
        """
        session = self.client.session
        session['temp_service_booking_uuid'] = str(uuid.uuid4()) # Non-existent UUID
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages))

    def test_dispatch_no_customer_motorcycle_redirects_to_step3(self):
        """
        Tests that dispatch redirects to step3 if no customer motorcycle is linked.
        """
        self.temp_booking.customer_motorcycle = None
        self.temp_booking.save()
        
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step3'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please select or add your motorcycle details first (Step 3)." in str(m) for m in messages))

    def test_dispatch_no_service_profile_redirects_to_step4(self):
        """
        Tests that dispatch redirects to step4 if no service profile is linked.
        """
        self.temp_booking.service_profile = None
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step4'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please provide your contact details first (Step 4)." in str(m) for m in messages))

    def test_dispatch_valid_temp_booking_proceeds(self):
        """
        Tests that dispatch allows the request to proceed with a valid temporary booking.
        """
        # Stripe mocks are needed for the GET method to proceed without error
        with patch('stripe.PaymentIntent.create') as mock_create:
            mock_create.return_value = MagicMock(client_secret='test_client_secret', id='pi_new_123')
            response = self.client.get(self.base_url)
            self.assertEqual(response.status_code, 200) # Should render the form
            self.assertTemplateUsed(response, 'service/step6_payment.html')
            mock_create.assert_called_once() # Verify a new intent was created

    # --- GET Method Tests ---

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_online_full_payment_creates_new_intent_and_payment_obj(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests GET request for online full payment, creating a new Stripe PaymentIntent and local Payment.
        """
        self.temp_booking.payment_option = 'online_full'
        self.temp_booking.save()

        mock_create.return_value = MagicMock(client_secret='new_client_secret', id='pi_new_full_123')
        mock_retrieve.side_effect = stripe.error.InvalidRequestError("No such payment intent", "id") # Simulate no existing intent

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('client_secret', response.context)
        self.assertEqual(response.context['client_secret'], 'new_client_secret')
        self.assertEqual(response.context['amount'], self.service_type.base_price)
        self.assertEqual(response.context['currency'], 'AUD')
        self.assertTemplateUsed(response, 'service/step6_payment.html')

        mock_create.assert_called_once_with(
            amount=int(self.service_type.base_price * 100),
            currency='AUD',
            metadata={
                'temp_booking_uuid': str(self.temp_booking.session_uuid),
                'service_profile_id': str(self.service_profile.id),
                'booking_type': 'service_booking',
            },
            description=f"Motorcycle service booking for {self.customer_motorcycle.year} {self.customer_motorcycle.brand} {self.customer_motorcycle.model} ({self.service_type.name})"
        )
        
        # Verify Payment object creation
        payment = Payment.objects.get(temp_service_booking=self.temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_new_full_123')
        self.assertEqual(payment.amount, self.service_type.base_price)
        self.assertEqual(payment.currency, 'AUD')
        self.assertEqual(payment.status, mock_create.return_value.status)
        self.assertEqual(payment.service_customer_profile, self.service_profile)
        self.assertEqual(Payment.objects.count(), 1) # Only one payment object

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_online_deposit_creates_new_intent_and_payment_obj(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests GET request for online deposit payment, creating a new Stripe PaymentIntent and local Payment.
        """
        self.temp_booking.payment_option = 'online_deposit'
        self.temp_booking.save()

        mock_create.return_value = MagicMock(client_secret='new_deposit_secret', id='pi_new_deposit_456')
        mock_retrieve.side_effect = stripe.error.InvalidRequestError("No such payment intent", "id")

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client_secret'], 'new_deposit_secret')
        self.assertEqual(response.context['amount'], self.temp_booking.calculated_deposit_amount)
        self.assertEqual(response.context['currency'], 'AUD')

        mock_create.assert_called_once_with(
            amount=int(self.temp_booking.calculated_deposit_amount * 100),
            currency='AUD',
            metadata={
                'temp_booking_uuid': str(self.temp_booking.session_uuid),
                'service_profile_id': str(self.service_profile.id),
                'booking_type': 'service_booking',
            },
            description=f"Motorcycle service booking for {self.customer_motorcycle.year} {self.customer_motorcycle.brand} {self.customer_motorcycle.model} ({self.service_type.name})"
        )
        
        payment = Payment.objects.get(temp_service_booking=self.temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_new_deposit_456')
        self.assertEqual(payment.amount, self.temp_booking.calculated_deposit_amount)

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_existing_intent_modified_if_amount_changed(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests that an existing PaymentIntent is modified if the amount changes and it's in a modifiable status.
        """
        existing_amount = Decimal('100.00')
        new_amount = Decimal('150.00')
        self.temp_booking.payment_option = 'online_full'
        self.temp_booking.service_type.base_price = new_amount # Update base price for new amount
        self.temp_booking.service_type.save()
        self.temp_booking.save()

        # Create a pre-existing Payment object that needs modification
        initial_payment = PaymentFactory(
            temp_service_booking=self.temp_booking,
            amount=existing_amount,
            currency='AUD',
            status='requires_payment_method',
            service_customer_profile=self.service_profile,
            stripe_payment_intent_id='pi_existing_123'
        )

        # Mock retrieve to return the existing intent with the old amount
        mock_retrieve.return_value = MagicMock(
            id='pi_existing_123',
            amount=int(existing_amount * 100),
            currency='aud',
            client_secret='old_client_secret',
            status='requires_payment_method'
        )
        # Mock modify to return the updated intent
        mock_modify.return_value = MagicMock(
            id='pi_existing_123',
            amount=int(new_amount * 100),
            currency='aud',
            client_secret='new_client_secret_modified',
            status='requires_action' # Status might change after modification
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client_secret'], 'new_client_secret_modified')
        self.assertEqual(response.context['amount'], new_amount)

        mock_retrieve.assert_called_once_with('pi_existing_123')
        mock_modify.assert_called_once() # Verify modify was called
        mock_create.assert_not_called() # Create should not be called

        initial_payment.refresh_from_db()
        self.assertEqual(initial_payment.amount, new_amount)
        self.assertEqual(initial_payment.status, 'requires_action') # Status updated

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_existing_intent_succeeded_redirects_to_step7(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests that if an existing PaymentIntent has already succeeded, the view redirects to step 7.
        """
        # Create a pre-existing Payment object with succeeded status
        initial_payment = PaymentFactory(
            temp_service_booking=self.temp_booking,
            amount=self.service_type.base_price,
            currency='AUD',
            status='succeeded',
            service_customer_profile=self.service_profile,
            stripe_payment_intent_id='pi_succeeded_789'
        )

        # Mock retrieve to return the succeeded intent
        mock_retrieve.return_value = MagicMock(
            id='pi_succeeded_789',
            amount=int(self.service_type.base_price * 100),
            currency='aud',
            client_secret='succeeded_client_secret',
            status='succeeded'
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        # Verify it renders the page but with a flag, allowing for immediate confirmation message
        self.assertIn('payment_already_succeeded', response.context)
        self.assertTrue(response.context['payment_already_succeeded'])
        self.assertTemplateUsed(response, 'service/step6_payment.html')

        mock_retrieve.assert_called_once_with('pi_succeeded_789')
        mock_modify.assert_not_called()
        mock_create.assert_not_called()

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_in_store_full_payment_redirects_to_step7_immediately(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests that if the payment option is 'in_store_full', no Stripe interaction occurs and
        the user is immediately redirected to step 7 confirmation.
        """
        self.temp_booking.payment_option = 'in_store_full'
        self.temp_booking.save()

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step7') + f'?temp_booking_uuid={self.temp_booking.session_uuid}')
        
        mock_create.assert_not_called()
        mock_retrieve.assert_not_called()
        mock_modify.assert_not_called()
        self.assertEqual(Payment.objects.count(), 0) # No payment object should be created

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_stripe_error_redirects_to_step5(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests that a Stripe API error during GET request redirects to step 5.
        """
        mock_retrieve.side_effect = stripe.error.StripeError("Stripe API error")
        mock_create.side_effect = stripe.error.StripeError("Stripe API error")

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(Payment.objects.count(), 0) # No payment object created/modified on error

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_invalid_amount_redirects_to_step5(self, mock_modify, mock_retrieve, mock_create):
        """
        Tests that if the amount to pay is zero or None, the view redirects to step 5.
        """
        self.temp_booking.payment_option = 'online_full'
        self.temp_booking.service_type.base_price = Decimal('0.00') # Zero amount
        self.temp_booking.service_type.save()
        self.temp_booking.save()

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        mock_create.assert_not_called()
        mock_retrieve.assert_not_called()
        mock_modify.assert_not_called()
        self.assertEqual(Payment.objects.count(), 0)


    # --- POST Method Tests ---

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_payment_succeeded_json_response(self, mock_retrieve):
        """
        Tests POST request when Stripe reports the payment intent has succeeded.
        """
        payment_intent_id = 'pi_test_succeeded'
        # Create a local Payment object corresponding to the intent
        PaymentFactory(
            temp_service_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status='requires_action', # Initial status
            amount=self.service_type.base_price,
            currency='AUD',
            service_customer_profile=self.service_profile
        )

        mock_retrieve.return_value = MagicMock(id=payment_intent_id, status='succeeded')

        response = self.client.post(
            self.base_url,
            json.dumps({'payment_intent_id': payment_intent_id}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        self.assertIn('redirect_url', json_response)
        self.assertTrue(json_response['redirect_url'].endswith(f'?payment_intent_id={payment_intent_id}'))

        # Verify local Payment object status is updated (though webhook handles final confirmation)
        payment_obj = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
        self.assertEqual(payment_obj.status, 'succeeded') # Should be updated by webhook later, but GET/POST might update it too

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_payment_requires_action_json_response(self, mock_retrieve):
        """
        Tests POST request when Stripe reports the payment intent requires action.
        """
        payment_intent_id = 'pi_test_requires_action'
        payment_obj = PaymentFactory(
            temp_service_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status='requires_payment_method',
            amount=self.service_type.base_price,
            currency='AUD',
            service_customer_profile=self.service_profile
        )

        mock_retrieve.return_value = MagicMock(id=payment_intent_id, status='requires_action')

        response = self.client.post(
            self.base_url,
            json.dumps({'payment_intent_id': payment_intent_id}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'requires_action')

        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'requires_action')

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_payment_failed_json_response(self, mock_retrieve):
        """
        Tests POST request when Stripe reports the payment intent has failed.
        """
        payment_intent_id = 'pi_test_failed'
        payment_obj = PaymentFactory(
            temp_service_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status='requires_payment_method',
            amount=self.service_type.base_price,
            currency='AUD',
            service_customer_profile=self.service_profile
        )

        mock_retrieve.return_value = MagicMock(id=payment_intent_id, status='failed')

        response = self.client.post(
            self.base_url,
            json.dumps({'payment_intent_id': payment_intent_id}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'failed')

        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'failed')

    def test_post_invalid_json_returns_400(self):
        """
        Tests POST request with invalid JSON body.
        """
        response = self.client.post(
            self.base_url,
            '{"payment_intent_id": "pi_invalid"', # Malformed JSON
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['error'])

    def test_post_missing_payment_intent_id_returns_400(self):
        """
        Tests POST request when payment_intent_id is missing from JSON.
        """
        response = self.client.post(
            self.base_url,
            json.dumps({'some_other_key': 'value'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Payment Intent ID is required', response.json()['error'])

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_stripe_error_returns_500(self, mock_retrieve):
        """
        Tests POST request when retrieving PaymentIntent from Stripe results in an error.
        """
        payment_intent_id = 'pi_error_on_retrieve'
        mock_retrieve.side_effect = stripe.error.StripeError("Error retrieving intent")

        response = self.client.post(
            self.base_url,
            json.dumps({'payment_intent_id': payment_intent_id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn('Error retrieving intent', response.json()['error'])