                                                  

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import datetime
import uuid
from service.forms.step4_service_profile_form import ServiceBookingUserForm
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
)

User = get_user_model()

class Step4ServiceProfileViewTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.factory = RequestFactory()
        cls.user_password = 'testpassword123'
        cls.user = UserFactory(password=cls.user_password)                          
        cls.other_user = UserFactory(username="otheruser", email="other@example.com", password=cls.user_password)

        cls.service_type = ServiceTypeFactory()
        cls.service_settings = ServiceSettingsFactory()                        
        cls.base_url = reverse('service:service_book_step4')

    def setUp(self):
        
                                                
        TempServiceBooking.objects.all().delete()
        ServiceProfile.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

                                                
                                                            
        self.motorcycle_for_temp_booking = CustomerMotorcycleFactory(
            brand="Honda", model="CBR", year=2020, rego="STEP4MC"
        )
                                                                                       

        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=datetime.date.today() + datetime.timedelta(days=10),
            customer_motorcycle=self.motorcycle_for_temp_booking,                              
            service_profile=None                                                
        )

                                              
        session = self.client.session
                                                                        
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()
        
                                                                                    
        self.valid_post_data = {
            'name': 'Test User Name',
            'email': 'testuser@example.com',
            'phone_number': '0123456789',
            'address_line_1': '123 Test St',
            'address_line_2': '',
            'city': 'Testville',
            'state': 'TS',
            'post_code': '12345',
            'country': 'Testland',
        }

                                   

    def test_dispatch_no_temp_booking_uuid_in_session_redirects(self):
        self.client.logout()                       
        session = self.client.session
                                                                        
        if 'temp_service_booking_uuid' in session:
            del session['temp_service_booking_uuid']
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
                                                                     
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired or is invalid." in str(m) for m in messages))


    def test_dispatch_invalid_temp_booking_uuid_redirects(self):
        session = self.client.session
                                                                        
        session['temp_service_booking_uuid'] = str(uuid.uuid4())                    
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'))
        messages = list(get_messages(response.wsgi_request))
                                                                   
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages))


    def test_dispatch_no_motorcycle_on_temp_booking_redirects_to_step3(self):
        self.temp_booking.customer_motorcycle = None
        self.temp_booking.save()
                                                     
        session = self.client.session
                                                                        
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step3'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please select or add your motorcycle details first (Step 3)." in str(m) for m in messages))

    def test_dispatch_valid_temp_booking_proceeds(self):
                                                         
                                                
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)                         
        self.assertTemplateUsed(response, 'service/step4_service_profile.html')

                              

    def test_get_anonymous_user_renders_blank_form(self):
        self.client.logout()                   
                                     
        session = self.client.session
                                                                        
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ServiceBookingUserForm)
        self.assertIsNone(response.context['form'].instance.pk)               

    def test_get_auth_user_no_profile_renders_blank_form(self):
        self.client.force_login(self.user)
                                                    
        ServiceProfile.objects.filter(user=self.user).delete()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ServiceBookingUserForm)
        self.assertIsNone(response.context['form'].instance.pk)               

    def test_get_auth_user_with_profile_renders_prefilled_form(self):
        self.client.force_login(self.user)
        user_profile = ServiceProfileFactory(user=self.user, name="Existing User Profile")

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, ServiceBookingUserForm)
        self.assertEqual(form.instance, user_profile)
        self.assertEqual(form.initial['name'], "Existing User Profile")

    def test_get_temp_booking_has_profile_precedence_over_user_profile(self):
        self.client.force_login(self.user)
        user_profile = ServiceProfileFactory(user=self.user, name="User's Own Profile")
                                                                                                
        temp_booking_profile = ServiceProfileFactory(name="Profile From TempBooking")
        self.temp_booking.service_profile = temp_booking_profile
        self.temp_booking.save()

                                                     
        session = self.client.session
                                                                        
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, ServiceBookingUserForm)
        self.assertEqual(form.instance, temp_booking_profile)                                       
        self.assertEqual(form.initial['name'], "Profile From TempBooking")


                               

    def test_post_anonymous_user_create_profile_valid_data(self):
        self.client.logout()
        session = self.client.session
                                                                        
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        initial_profile_count = ServiceProfile.objects.count()
        response = self.client.post(self.base_url, self.valid_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count + 1)

        new_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        self.assertIsNone(new_profile.user)                               

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.service_profile, new_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, new_profile)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your details have been saved successfully." in str(m) for m in messages))

    def test_post_auth_user_no_profile_create_profile_valid_data(self):
        self.client.force_login(self.user)
        ServiceProfile.objects.filter(user=self.user).delete()                    

        initial_profile_count = ServiceProfile.objects.count()
        response = self.client.post(self.base_url, self.valid_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count + 1)

        new_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        self.assertEqual(new_profile.user, self.user)                        

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.service_profile, new_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, new_profile)

    def test_post_auth_user_with_profile_update_profile_valid_data(self):
        self.client.force_login(self.user)
        existing_profile = ServiceProfileFactory(user=self.user, name="Old Name", email="old_email@example.com")
        self.temp_booking.service_profile = existing_profile                                
        self.temp_booking.save()
        
        session = self.client.session                  
                                                                        
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()

        updated_data = self.valid_post_data.copy()
        updated_data['name'] = "Updated Name"
        updated_data['email'] = existing_profile.email                                     

        initial_profile_count = ServiceProfile.objects.count()
        response = self.client.post(self.base_url, updated_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step5'))
        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count)                 

        existing_profile.refresh_from_db()
        self.assertEqual(existing_profile.name, "Updated Name")
        self.assertEqual(existing_profile.user, self.user)

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.service_profile, existing_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, existing_profile)

    def test_post_invalid_data_rerenders_form_with_errors(self):
        self.client.force_login(self.user)
        invalid_data = self.valid_post_data.copy()
        invalid_data['email'] = "notanemail"                

        initial_profile_count = ServiceProfile.objects.count()
        motorcycle_initial_profile = self.motorcycle_for_temp_booking.service_profile

        response = self.client.post(self.base_url, invalid_data)

        self.assertEqual(response.status_code, 200)            
        self.assertTemplateUsed(response, 'service/step4_service_profile.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)                        

        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count)                 
        
        self.temp_booking.refresh_from_db()                                                
        self.assertIsNone(self.temp_booking.service_profile)

        self.motorcycle_for_temp_booking.refresh_from_db()                                             
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, motorcycle_initial_profile)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please correct the errors below." in str(m) for m in messages))

    def test_post_updates_motorcycle_profile_if_not_already_set(self):
        self.client.force_login(self.user)
                                                                           
        self.motorcycle_for_temp_booking.service_profile = None
        self.motorcycle_for_temp_booking.save()

        response = self.client.post(self.base_url, self.valid_post_data)
        self.assertEqual(response.status_code, 302)

        new_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        self.motorcycle_for_temp_booking.refresh_from_db()
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, new_profile)

    def test_post_updates_motorcycle_profile_if_different(self):
        self.client.force_login(self.user)
        old_motorcycle_profile = ServiceProfileFactory(name="Old Bike Owner Profile")
        self.motorcycle_for_temp_booking.service_profile = old_motorcycle_profile
        self.motorcycle_for_temp_booking.save()

                                                                   
        response = self.client.post(self.base_url, self.valid_post_data)
        self.assertEqual(response.status_code, 302)

                                                                
        form_submitted_profile = ServiceProfile.objects.get(email=self.valid_post_data['email'])
        
        self.motorcycle_for_temp_booking.refresh_from_db()
                                                                                                    
        self.assertEqual(self.motorcycle_for_temp_booking.service_profile, form_submitted_profile)
        self.assertNotEqual(self.motorcycle_for_temp_booking.service_profile, old_motorcycle_profile)
