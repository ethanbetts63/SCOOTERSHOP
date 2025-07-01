                                                                       

from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import uuid
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
import stripe

from payments.models import Payment
from inventory.models import TempSalesBooking, SalesProfile, Motorcycle, InventorySettings
                                           
from inventory.tests.test_helpers.model_factories import (
    UserFactory,
    SalesProfileFactory,
    TempSalesBookingFactory,
    MotorcycleFactory,
    InventorySettingsFactory,
    PaymentFactory,
)

User = get_user_model()

                                 
@patch('stripe.api_key', 'sk_test_mock_key')
class Step3PaymentViewTest(TestCase):
    """
    Tests for the Step3PaymentView (dispatch, GET, and POST methods).
    This class tests the Stripe payment integration for sales bookings.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.user = UserFactory()
        cls.inventory_settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('200.00'),
            currency_code='AUD',
        )
        cls.motorcycle = MotorcycleFactory(price=Decimal('15000.00'))
        cls.base_url = reverse('inventory:step3_payment')

    def setUp(self):
        """
        Set up for each test method.
        """
        TempSalesBooking.objects.all().delete()
        Payment.objects.all().delete()
        SalesProfile.objects.all().delete()

        self.sales_profile = SalesProfileFactory(user=self.user)
        self.temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=self.inventory_settings.deposit_amount,
            deposit_required_for_flow=True,
        )

        session = self.client.session
        session['temp_sales_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

                                   

    def test_dispatch_no_temp_booking_uuid_in_session_redirects(self):
        """
        Tests that dispatch redirects if no temp_sales_booking_uuid is in session.
        """
        self.client.logout()
        session = self.client.session
        if 'temp_sales_booking_uuid' in session:
            del session['temp_sales_booking_uuid']
        session.save()

        response = self.client.get(self.base_url)
        self.assertRedirects(response, reverse('inventory:used'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired or is invalid." in str(m) for m in messages))

    def test_dispatch_invalid_temp_booking_uuid_redirects(self):
        """
        Tests that dispatch redirects if an invalid temp_sales_booking_uuid is in session.
        """
        session = self.client.session
        session['temp_sales_booking_uuid'] = str(uuid.uuid4())
        session.save()

        response = self.client.get(self.base_url)
        self.assertRedirects(response, reverse('inventory:used'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages))

    def test_dispatch_no_motorcycle_redirects(self):
        """
        Tests dispatch redirects if no motorcycle is linked to the booking.
        """
        self.temp_booking.motorcycle = None
        self.temp_booking.save()
        
        response = self.client.get(self.base_url)
        self.assertRedirects(response, reverse('inventory:used'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please select a motorcycle first." in str(m) for m in messages))

    def test_dispatch_no_sales_profile_redirects(self):
        """
        Tests dispatch redirects if no sales profile is linked to the booking.
        """
        self.temp_booking.sales_profile = None
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please provide your contact details first." in str(m) for m in messages))

    def test_dispatch_deposit_not_required_redirects_to_confirmation(self):
        """
        Tests that dispatch redirects to confirmation if deposit is not required.
        """
        self.temp_booking.deposit_required_for_flow = False
        self.temp_booking.stripe_payment_intent_id = 'pi_12345'
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        redirect_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={self.temp_booking.stripe_payment_intent_id}'
        self.assertRedirects(response, redirect_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Payment is not required for this type of booking." in str(m) for m in messages))

                              

    @patch('inventory.views.user_views.step3_payment_view.create_or_update_sales_payment_intent')
    def test_get_creates_new_intent_and_payment_obj(self, mock_create_update):
        """
        Tests GET request creates a new Stripe PaymentIntent and local Payment object.
        """
        mock_intent = MagicMock(client_secret='new_client_secret', id='pi_new_123')
                                                                                    
        mock_payment = PaymentFactory.build(stripe_payment_intent_id=mock_intent.id, temp_sales_booking=self.temp_booking)
        mock_create_update.return_value = (mock_intent, mock_payment)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('client_secret', response.context)
        self.assertEqual(response.context['client_secret'], 'new_client_secret')
        self.assertEqual(response.context['amount'], self.inventory_settings.deposit_amount)
        self.assertTemplateUsed(response, 'inventory/step3_payment.html')

        mock_create_update.assert_called_once()


    @patch('inventory.views.user_views.step3_payment_view.create_or_update_sales_payment_intent')
    def test_get_invalid_amount_redirects(self, mock_create_update):
        """
        Tests redirect if the amount to pay is zero or None.
        """
        self.temp_booking.amount_paid = Decimal('0.00')
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("The amount to pay is invalid." in str(m) for m in messages))
        mock_create_update.assert_not_called()

    @patch('inventory.views.user_views.step3_payment_view.create_or_update_sales_payment_intent')
    def test_get_stripe_error_redirects(self, mock_create_update):
        """
        Tests redirect on Stripe API error during GET request.
        """
        mock_create_update.side_effect = stripe.error.StripeError("Stripe API error")

        response = self.client.get(self.base_url)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Payment system error:" in str(m) for m in messages))

                               

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_payment_succeeded(self, mock_retrieve):
        """
        Tests POST when Stripe reports payment succeeded.
        """
        payment_intent_id = 'pi_test_succeeded'
                                                                                                  
                                                              
        PaymentFactory(
            temp_sales_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status='requires_payment_method',
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
        self.assertTrue(json_response['redirect_url'].startswith(reverse('inventory:step4_confirmation')))

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_payment_requires_action(self, mock_retrieve):
        """
        Tests POST when Stripe reports payment requires action.
        The local Payment object's status is expected to be updated by the webhook.
        """
        payment_intent_id = 'pi_test_requires_action'
                                                                                                  
                                                              
        PaymentFactory(
            temp_sales_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status='requires_payment_method',
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
                                                                            
                                       
                                                                 

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_payment_failed(self, mock_retrieve):
        """
        Tests POST when Stripe reports payment failed.
        The local Payment object's status is expected to be updated by the webhook.
        """
        payment_intent_id = 'pi_test_failed'
                                                                                                  
                                                              
        PaymentFactory(
            temp_sales_booking=self.temp_booking,
            stripe_payment_intent_id=payment_intent_id,
            status='requires_payment_method',
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
                                                                            
                                       
                                                        

    def test_post_invalid_json_returns_400(self):
        """
        Tests POST with invalid JSON.
        """
        response = self.client.post(
            self.base_url,
            '{"invalid_json": "test"',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['error'])

    def test_post_missing_payment_intent_id_returns_400(self):
        """
        Tests POST with missing payment_intent_id.
        """
        response = self.client.post(
            self.base_url,
            json.dumps({'other_key': 'value'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Payment Intent ID is required', response.json()['error'])

    @patch('stripe.PaymentIntent.retrieve')
    def test_post_stripe_error_returns_500(self, mock_retrieve):
        """
        Tests POST when Stripe API call fails.
        """
        mock_retrieve.side_effect = stripe.error.StripeError("Stripe error")
        response = self.client.post(
            self.base_url,
            json.dumps({'payment_intent_id': 'pi_123'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn('Stripe error', response.json()['error'])

