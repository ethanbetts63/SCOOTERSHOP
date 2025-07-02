                                                                      

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import datetime
from datetime import time
import uuid
from decimal import Decimal
from unittest.mock import patch
from django.http import HttpResponse
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle, ServiceSettings
from service.forms.step5_payment_choice_and_terms_form import (
    PaymentOptionForm,
    PAYMENT_OPTION_DEPOSIT,
    PAYMENT_OPTION_FULL_ONLINE,
    PAYMENT_OPTION_INSTORE
)
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
)

User = get_user_model()

class Step5PaymentDropoffAndTermsViewTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.factory = RequestFactory()
        cls.user_password = 'testpassword123'
        cls.user = UserFactory(password=cls.user_password)                          
        
                                                                                        
        cls.service_settings = ServiceSettingsFactory(
            enable_online_full_payment=True,
            enable_online_deposit=True,
            enable_instore_full_payment=True,
            enable_deposit=True,                                          
            deposit_calc_method='FLAT_FEE',
            deposit_flat_fee_amount=Decimal('50.00'),
            currency_symbol='$',
            max_advance_dropoff_days=10,                               
            latest_same_day_dropoff_time=time(12, 0),                  
            drop_off_start_time=time(9, 0),
            drop_off_end_time=time(17, 0),
        )
        cls.service_type = ServiceTypeFactory(base_price=Decimal('250.00'))
        cls.base_url = reverse('service:service_book_step5')

    def setUp(self):
        
        TempServiceBooking.objects.all().delete()
        ServiceProfile.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

                                                                                 
        self.customer_motorcycle = CustomerMotorcycleFactory(
            brand="Honda", model="CBR", year=2020, rego="TESTMC"
        )
        self.service_profile = ServiceProfileFactory(user=self.user, email="test@example.com")

                                                  
        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=datetime.date.today() + datetime.timedelta(days=10),                             
            customer_motorcycle=self.customer_motorcycle,                     
            service_profile=self.service_profile,                     
            dropoff_date=None,                           
            dropoff_time=None,                           
            payment_method=None,                           
            calculated_deposit_amount=Decimal('50.00')                  
        )

                                              
        session = self.client.session
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()
        
                                                                                    
        self.valid_post_data = {
            'dropoff_date': (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
            'dropoff_time': '10:30',
            'payment_method': PAYMENT_OPTION_FULL_ONLINE,
            'service_terms_accepted': True,
        }

                                   

    def test_dispatch_no_temp_booking_uuid_in_session_redirects_to_service_home(self):
        
        self.client.logout()                       
        session = self.client.session
        if 'temp_service_booking_uuid' in session:
            del session['temp_service_booking_uuid']
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired." in str(m) for m in messages))

    def test_dispatch_invalid_temp_booking_uuid_redirects_to_service_home(self):
        
        session = self.client.session
        session['temp_service_booking_uuid'] = str(uuid.uuid4())                    
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages))

    def test_dispatch_no_service_profile_redirects_to_step4(self):
        
        self.temp_booking.service_profile = None
        self.temp_booking.save()
        
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step4'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please complete your personal details first (Step 4)." in str(m) for m in messages))

    def test_dispatch_no_service_settings_redirects_to_service_home(self):
        
        ServiceSettings.objects.all().delete()                           
        
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Service settings are not configured." in str(m) for m in messages))

    def test_dispatch_valid_temp_booking_proceeds(self):
        
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)                         
        self.assertTemplateUsed(response, 'service/step5_payment_dropoff_and_terms.html')

                              

    def test_get_renders_form_with_initial_data_from_temp_booking(self):
        
                                               
        self.temp_booking.dropoff_date = datetime.date.today() + datetime.timedelta(days=5)
        self.temp_booking.dropoff_time = time(11, 0)
        self.temp_booking.payment_method = PAYMENT_OPTION_DEPOSIT
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, PaymentOptionForm)
        self.assertEqual(form.initial['dropoff_date'], self.temp_booking.dropoff_date)
        self.assertEqual(form.initial['dropoff_time'], self.temp_booking.dropoff_time)
        self.assertEqual(form.initial['payment_method'], self.temp_booking.payment_method)

    def test_get_context_data_same_day_dropoff_only_when_max_advance_is_zero(self):
        
        self.service_settings.max_advance_dropoff_days = 0
        self.service_settings.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_same_day_dropoff_only'])
                                                                   
        form = response.context['form']
        self.assertEqual(form.initial['dropoff_date'], self.temp_booking.service_date)


                               

    def test_post_valid_data_updates_temp_booking_and_redirects_to_step6(self):
        
        initial_dropoff_date = self.temp_booking.dropoff_date
        initial_dropoff_time = self.temp_booking.dropoff_time
        initial_payment_method = self.temp_booking.payment_method

        response = self.client.post(self.base_url, self.valid_post_data)

        self.assertEqual(response.status_code, 302)
                                                                                            
                                                                                                       
        self.assertRedirects(response, reverse('service:service_book_step6'), fetch_redirect_response=False)

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.dropoff_date, datetime.date.fromisoformat(self.valid_post_data['dropoff_date']))
        self.assertEqual(self.temp_booking.dropoff_time, datetime.time.fromisoformat(self.valid_post_data['dropoff_time']))
        self.assertEqual(self.temp_booking.payment_method, self.valid_post_data['payment_method'])
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Drop-off and payment details have been saved successfully." in str(m) for m in messages))


    def test_post_invalid_data_rerenders_form_with_errors(self):
        
        invalid_data = self.valid_post_data.copy()
        invalid_data['dropoff_date'] = 'invalid-date'                      
        invalid_data['service_terms_accepted'] = False               

        response = self.client.post(self.base_url, invalid_data)

        self.assertEqual(response.status_code, 200)                   
        self.assertTemplateUsed(response, 'service/step5_payment_dropoff_and_terms.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn('service_terms_accepted', form.errors)                                

        self.temp_booking.refresh_from_db()                                     
        self.assertIsNone(self.temp_booking.dropoff_date)
        self.assertIsNone(self.temp_booking.dropoff_time)
        self.assertIsNone(self.temp_booking.payment_method)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please correct the errors highlighted below." in str(m) for m in messages))

    def test_post_dropoff_date_after_service_date_is_invalid(self):
        
        invalid_data = self.valid_post_data.copy()
                                                          
        invalid_data['dropoff_date'] = (self.temp_booking.service_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        response = self.client.post(self.base_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn("Drop-off date cannot be after the service date.", form.errors['dropoff_date'][0])

    def test_post_dropoff_date_too_far_in_advance_is_invalid(self):
        
                                                         
        invalid_data = self.valid_post_data.copy()
                                                       
        invalid_data['dropoff_date'] = (self.temp_booking.service_date - datetime.timedelta(days=11)).strftime('%Y-%m-%d')

        response = self.client.post(self.base_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn(f"Drop-off cannot be scheduled more than {self.service_settings.max_advance_dropoff_days} days in advance of the service.", form.errors['dropoff_date'][0])

    def test_post_same_day_dropoff_time_in_past_is_invalid(self):                                                              
        self.temp_booking.service_date = datetime.date.today()
        self.temp_booking.save()
        self.service_settings.max_advance_dropoff_days = 0                          
        self.service_settings.save()                                                                        
                                                      
        with self.settings(USE_TZ=True, TIME_ZONE='Australia/Perth'):
            with patch('django.utils.timezone.localtime') as mock_localtime:
                                                                                      
                mock_localtime.return_value = datetime.datetime.combine(
                    datetime.date.today(),
                    time(11, 0),                                
                    tzinfo=datetime.timezone.utc                                               
                ).astimezone(datetime.timezone.utc)                                                           

                invalid_data = self.valid_post_data.copy()
                invalid_data['dropoff_date'] = datetime.date.today().strftime('%Y-%m-%d')
                invalid_data['dropoff_time'] = '10:00'                                         

                response = self.client.post(self.base_url, invalid_data)
                self.assertEqual(response.status_code, 200)
                form = response.context['form']
                self.assertFalse(form.is_valid())
                self.assertIn('dropoff_time', form.errors)
                self.assertIn("You cannot select a drop-off time that has already passed today.", form.errors['dropoff_time'][0])                                                                                                   
                                      
    def test_payment_method_choices_are_correctly_populated(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        
        expected_choices = [
            (PAYMENT_OPTION_DEPOSIT, f"Pay Deposit Online (${self.service_settings.deposit_flat_fee_amount:.2f})"),
            (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"),
            (PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"),
        ]
        self.assertEqual(list(form.fields['payment_method'].choices), expected_choices)


    @patch('service.views.user_views.Step6PaymentView.dispatch')
    def test_post_payment_method_deposit_online(self, mock_step6_dispatch):                                                                 
        mock_step6_dispatch.return_value = HttpResponse(status=200) 

        valid_data = self.valid_post_data.copy()
        valid_data['payment_method'] = PAYMENT_OPTION_DEPOSIT
        response = self.client.post(self.base_url, valid_data)
        
                                                            
        self.assertEqual(response.status_code, 302)
                                                                                                                        
        self.assertRedirects(response, reverse('service:service_book_step6')) 
        
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.payment_method, PAYMENT_OPTION_DEPOSIT)
        mock_step6_dispatch.assert_called_once()