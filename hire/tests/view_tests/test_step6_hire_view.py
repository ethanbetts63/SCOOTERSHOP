                                               

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from decimal import Decimal
import datetime
import uuid
from unittest.mock import patch, MagicMock
import json
import stripe
from django.utils import timezone                
from datetime import timedelta                    
from django.conf import settings                
from django.contrib.auth import get_user_model                        

               
from hire.models import TempHireBooking, HireBooking
from payments.models import Payment
from dashboard.models import HireSettings

                        
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_temp_hire_booking,
    create_driver_profile,
    create_user,                     
)

class PaymentDetailsViewTest(TestCase):
    """
    Tests for the PaymentDetailsView (Step 6 of the hire booking process).
    """

    def setUp(self):
        """
        Set up common URLs, HireSettings, Motorcycle, and DriverProfile.
        Also logs in the test client with the user associated with the driver profile.
        """
        self.client = Client()
        self.step6_url = reverse('hire:step6_payment_details')
        self.step2_url = reverse('hire:step2_choose_bike')
        self.step5_url = reverse('hire:step5_summary_payment_options')
        self.step7_url_base = reverse('hire:step7_confirmation')

                                                                                
        self.hire_settings = create_hire_settings(
            deposit_enabled=True,
            deposit_percentage=Decimal('20.00'),
            enable_online_full_payment=True,
            enable_online_deposit_payment=True,
            enable_in_store_full_payment=True,                                            
            hire_pricing_strategy='24_hour_customer_friendly'
        )

                                                  
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00'),
            is_available=True,
            engine_size=125
        )
        
                                                                     
                                                                                          
        User = get_user_model()
        self.user = create_user(username='testuser_step6', password='password123')
        self.driver_profile = create_driver_profile(user=self.user)


                                               
        self.client.login(username='testuser_step6', password='password123')


                                    
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
            payment_option=payment_option,                                  
            currency='AUD'                             
        )
        session = self.client.session
        session['temp_booking_id'] = temp_booking.id
                                                                                                                      
        session.save()
        return temp_booking

                               

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_success_online_full_payment(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request with valid temp_booking for online_full payment.
        Should create a Stripe PaymentIntent and render the payment page.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')

                                          
        mock_stripe_create.return_value = MagicMock(
            id='pi_test_full',
            client_secret='cs_test_full',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )
                                                                                           
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

                                                       
        payment = Payment.objects.get(temp_hire_booking=temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test_full')
        self.assertEqual(payment.amount, temp_booking.grand_total)
        self.assertEqual(payment.status, 'requires_payment_method')
                                             
        self.assertEqual(payment.driver_profile, self.driver_profile)


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_success_online_deposit_payment(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request with valid temp_booking for online_deposit payment.
        Should create a Stripe PaymentIntent for the deposit amount.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_deposit')

                                          
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

                                                       
        payment = Payment.objects.get(temp_hire_booking=temp_booking)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test_deposit')
        self.assertEqual(payment.amount, temp_booking.deposit_amount)
        self.assertEqual(payment.status, 'requires_payment_method')
                                             
        self.assertEqual(payment.driver_profile, self.driver_profile)


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_no_temp_booking_id_in_session(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request without temp_booking_id in session.
        Should redirect to step 2.
        """
                                              
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
        session['temp_booking_id'] = 99999                  
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
        self._create_and_set_temp_booking_in_session(payment_option='in_store_full')                     

        response = self.client.get(self.step6_url)
                                                                                             
        self.assertEqual(response.status_code, 302)                                           
        self.assertEqual(response.url, self.step5_url)                                       

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_existing_payment_intent_reused(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing Payment object with a valid PI exists.
        Should retrieve and reuse the existing PaymentIntent.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')
                                           
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,                                   
            stripe_payment_intent_id='pi_existing_test',
            amount=temp_booking.grand_total,
            currency='AUD',
            status='requires_payment_method',
            description='Existing booking payment'
        )

                                                                      
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_existing_test',
            client_secret='cs_existing_test',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )
                                     
                                                                                                                                 

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertEqual(response.context['client_secret'], 'cs_existing_test')
        self.assertEqual(response.context['amount'], temp_booking.grand_total)

        mock_stripe_retrieve.assert_called_once_with('pi_existing_test')
        mock_stripe_create.assert_not_called()                              

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.modify')
    def test_get_request_existing_payment_intent_modified_amount(self, mock_stripe_modify, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing Payment object exists but amount changed.
        Should modify the existing PaymentIntent.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full', grand_total=Decimal('300.00'))
                                                                   
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,                                   
            stripe_payment_intent_id='pi_existing_test_modify',
            amount=Decimal('200.00'),             
            currency='AUD',
            status='requires_payment_method',
            description='Existing booking payment'
        )

                                                                                        
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_existing_test_modify',
            client_secret='cs_existing_test_modify',
            amount=int(Decimal('200.00') * 100),                      
            currency='aud',
            status='requires_payment_method'
        )
                                                                   
        mock_stripe_modify.return_value = MagicMock(
            id='pi_existing_test_modify',
            client_secret='cs_existing_test_modify_returned',                                                     
            amount=int(temp_booking.grand_total * 100),                      
            currency='aud',
            status='requires_payment_method'
        )

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
                                                                                                      
                                                                                                                            
                                                                                                       
                                                                                    
                                                                                                                                          
                                                                                                                
                                                                       
                                                                                     
        self.assertEqual(response.context['client_secret'], 'cs_existing_test_modify_returned')
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
        mock_stripe_create.assert_not_called()                              

                                                 
        existing_payment.refresh_from_db()
        self.assertEqual(existing_payment.amount, temp_booking.grand_total)
        self.assertEqual(existing_payment.status, 'requires_payment_method')                                      

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_existing_payment_intent_creates_new_on_canceled(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing PI is canceled.
        Should create a new PaymentIntent and update the existing Payment object.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_canceled_original',                             
            amount=temp_booking.grand_total,
            currency='AUD',
            status='canceled',                 
            description='Existing booking payment - canceled'
        )

                                                                      
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_canceled_original',
            client_secret='cs_canceled_original',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='canceled'
        )
                                                             
        mock_stripe_create.return_value = MagicMock(
            id='pi_new_after_canceled',            
            client_secret='cs_new_after_canceled',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertEqual(response.context['client_secret'], 'cs_new_after_canceled')                                 

        mock_stripe_retrieve.assert_called_once_with('pi_canceled_original')
        mock_stripe_create.assert_called_once_with(
            amount=int(temp_booking.grand_total * 100),
            currency='AUD',
            metadata={
                'temp_booking_id': str(temp_booking.id),
                'user_id': str(self.driver_profile.id),
                'booking_type': 'hire_booking',
            },
            description=f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"
        )

                                                                               
        existing_payment.refresh_from_db()
        self.assertEqual(existing_payment.stripe_payment_intent_id, 'pi_new_after_canceled')
        self.assertEqual(existing_payment.status, 'requires_payment_method')


    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.retrieve')
    def test_get_request_existing_payment_intent_creates_new_on_failed(self, mock_stripe_retrieve, mock_stripe_create):
        """
        Test GET request when an existing PI is failed.
        Should create a new PaymentIntent and update the existing Payment object.
        """
        temp_booking = self._create_and_set_temp_booking_in_session(payment_option='online_full')
        existing_payment = Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_failed_original',               
            amount=temp_booking.grand_total,
            currency='AUD',
            status='failed',                 
            description='Existing booking payment - failed'
        )

                                                                    
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_failed_original',
            client_secret='cs_failed_original',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='failed'
        )
                                                             
        mock_stripe_create.return_value = MagicMock(
            id='pi_new_after_failed',            
            client_secret='cs_new_after_failed',
            amount=int(temp_booking.grand_total * 100),
            currency='aud',
            status='requires_payment_method'
        )

        response = self.client.get(self.step6_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step6_payment_details.html')
        self.assertEqual(response.context['client_secret'], 'cs_new_after_failed')                                 

        mock_stripe_retrieve.assert_called_once_with('pi_failed_original')
        mock_stripe_create.assert_called_once_with(
            amount=int(temp_booking.grand_total * 100),
            currency='AUD',
            metadata={
                'temp_booking_id': str(temp_booking.id),
                'user_id': str(self.driver_profile.id),
                'booking_type': 'hire_booking',
            },
            description=f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"
        )

                                                                               
        existing_payment.refresh_from_db()
        self.assertEqual(existing_payment.stripe_payment_intent_id, 'pi_new_after_failed')
        self.assertEqual(existing_payment.status, 'requires_payment_method')


                                

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

                                                                                                       
        payment.refresh_from_db()
                                                                                                    
                                                                                                        
                                        
                                                                                                         
                                                                        
        self.assertEqual(payment.status, 'requires_confirmation')


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

                                                                             
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_requires_action',
            status='requires_action'
        )

        post_data = {'payment_intent_id': 'pi_requires_action'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'requires_action')
                                            
        self.assertNotIn('redirect_url', json_response)

                                                                     
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
            stripe_payment_intent_id='pi_failed_post',               
            amount=temp_booking.grand_total,
            currency='AUD',
            status='requires_confirmation',                 
            description='Test payment for failure post'
        )

                                                                    
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_failed_post',
            status='failed'
        )

        post_data = {'payment_intent_id': 'pi_failed_post'}
        response = self.client.post(self.step6_url, json.dumps(post_data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'failed')
                                            
        self.assertNotIn('redirect_url', json_response)

                                                                     
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


    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.PaymentIntent.modify')
    def test_get_request_existing_payment_intent_succeeded(
        self,
        mock_stripe_modify,
        mock_stripe_create,
        mock_stripe_retrieve
    ):
        """
        Test GET request when an existing Payment object exists and its PI is succeeded.
        """
                 
                                                                    
                                                                       
        temp_booking = self._create_and_set_temp_booking_in_session(
            grand_total=Decimal('300.00'),
            payment_option='online_full'
        )
        Payment.objects.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,                     
            stripe_payment_intent_id='pi_succeeded_test',
            amount=Decimal('300.00'),                              
            currency='AUD',
            status='succeeded'
        )
        mock_stripe_retrieve.return_value = MagicMock(
            id='pi_succeeded_test',
            client_secret='cs_succeeded_test',
            amount=30000,                                 
            currency='aud',
            status='succeeded',
            metadata={
                'temp_booking_id': str(temp_booking.id),
                'user_id': str(self.driver_profile.id),
                'booking_type': 'hire_booking'
            }
        )

             
        response = self.client.get(self.step6_url)

                
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get('payment_already_succeeded'))
        self.assertIsNone(response.context.get('client_secret'))                                        
        self.assertEqual(response.context.get('amount'), Decimal('300.00'))                       
        self.assertEqual(response.context.get('currency'), 'AUD')
        self.assertEqual(response.context.get('temp_booking').id, temp_booking.id)
        self.assertEqual(response.context.get('stripe_publishable_key'), settings.STRIPE_PUBLISHABLE_KEY)
        mock_stripe_retrieve.assert_called_once_with('pi_succeeded_test')
        mock_stripe_create.assert_not_called()
        mock_stripe_modify.assert_not_called()
