import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
import datetime

from hire.models import TempHireBooking, DriverProfile
from dashboard.models import HireSettings
                                                                                                      

                             
from hire.tests.test_helpers.model_factories import (
    create_user,
    create_temp_hire_booking,
    create_hire_settings,
    create_driver_profile,
    create_motorcycle
)

User = get_user_model()

class TestHasAccountView(TestCase):
    """
    Test suite for the HasAccountView (Step 4 - Has Account).
    """
    def setUp(self):
        """
        Set up common test data and environment.
        """
                              
        self.client = Client()

                                       
        self.user = create_user(username="testuser", password="password123")
        self.client.login(username="testuser", password="password123")

                                                               
        self.hire_settings = create_hire_settings(
            deposit_enabled=True,                                                 
            default_deposit_calculation_method='percentage',
            deposit_percentage=Decimal('10.00')
        )

                                                          
        self.motorcycle = create_motorcycle(daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))

                                           
        self.pickup_date = timezone.now().date() + datetime.timedelta(days=3)
        self.return_date = self.pickup_date + datetime.timedelta(days=2)              
        self.temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=self.pickup_date,
            pickup_time=datetime.time(10,0),
            return_date=self.return_date,
            return_time=datetime.time(10,0),
                                                       
            total_hire_price=None,
            total_package_price=Decimal('0.00'),
            total_addons_price=Decimal('0.00'),
            grand_total=None,
            deposit_amount=None,
            currency='AUD'
        )

                                                    
        session = self.client.session
        session["temp_booking_uuid"] = str(self.temp_booking.session_uuid)
        session.save()

                          
        self.url = reverse("hire:step4_has_account")

                                                                                                          
        self.mock_license_photo = SimpleUploadedFile("license.jpg", b"file_content_license", "image/jpeg")
        self.mock_intl_license_photo = SimpleUploadedFile("intl_license.jpg", b"file_content_intl_license", "image/jpeg")
        self.mock_passport_photo = SimpleUploadedFile("passport.jpg", b"file_content_passport", "image/jpeg")
        self.mock_id_image = SimpleUploadedFile("id.jpg", b"file_content_id", "image/jpeg")
        self.mock_intl_id_image = SimpleUploadedFile("intl_id.jpg", b"file_content_intl_id", "image/jpeg")

                                               
        self.mock_calculated_prices = {
            'motorcycle_price': Decimal('200.00'),
            'package_price': Decimal('50.00'),
            'addons_total_price': Decimal('20.00'),
            'grand_total': Decimal('270.00'),
            'deposit_amount': Decimal('27.00'),             
            'currency': 'AUD'
        }

    def _get_valid_australian_driver_data(self, image_suffix=""):
        """ Helper to get valid POST data for an Australian resident.
            Returns a tuple: (form_data_dict, file_data_dict)
        """
        form_data = {
            'name': 'Test User Aus',
            'email': 'testaus@example.com',
            'phone_number': '0412345678',
            'address_line_1': '1 Test St',
            'city': 'Sydney',
            'state': 'NSW',
            'post_code': '2000',
            'country': 'Australia',
            'date_of_birth': '1990-01-01',
            'is_australian_resident': 'True',                                     
            'license_number': 'AUS123456',
            'license_expiry_date': (self.return_date + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
        }
        file_data = {
            'license_photo': SimpleUploadedFile(f"license{image_suffix}.jpg", b"file_content_license", "image/jpeg"),
            'id_image': SimpleUploadedFile(f"id_aus{image_suffix}.jpg", b"file_content_id_aus", "image/jpeg"),
        }
        return form_data, file_data

    def _get_valid_foreign_driver_data(self, image_suffix=""):
        """ Helper to get valid POST data for a foreign resident.
            Returns a tuple: (form_data_dict, file_data_dict)
        """
        form_data = {
            'name': 'Test User Foreign',
            'email': 'testforeign@example.com',
            'phone_number': '004412345678',                               
            'address_line_1': '1 Foreigner Ave',
            'city': 'London',
            'post_code': 'W1A 0AX',
            'country': 'United Kingdom',
            'date_of_birth': '1985-05-05',
            'is_australian_resident': 'False',                                     
            'international_license_issuing_country': 'United Kingdom',
            'international_license_expiry_date': (self.return_date + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
            'passport_number': 'GB123456789',
            'passport_expiry_date': (self.return_date + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
        }
        file_data = {
            'international_license_photo': SimpleUploadedFile(f"intl_license{image_suffix}.jpg", b"file_content_intl_license", "image/jpeg"),
            'passport_photo': SimpleUploadedFile(f"passport{image_suffix}.jpg", b"file_content_passport", "image/jpeg"),
            'international_id_image': SimpleUploadedFile(f"id_intl{image_suffix}.jpg", b"file_content_id_intl", "image/jpeg"),
        }
        return form_data, file_data

                               
    def test_get_authenticated_user_with_temp_booking_no_driver_profile(self):
        """ Test GET request when user is authenticated, has a temp_booking, but no DriverProfile. """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        self.assertIn("form", response.context)
        self.assertIn("temp_booking", response.context)
        self.assertEqual(response.context["temp_booking"], self.temp_booking)
        
        form = response.context["form"]
        self.assertIsInstance(form.instance, DriverProfile)
        self.assertIsNone(form.instance.pk)                                      
        self.assertEqual(form.instance.user, self.user)                                     

    def test_get_authenticated_user_with_temp_booking_existing_driver_profile(self):
        """ Test GET request when user has an existing DriverProfile. """
        existing_profile = create_driver_profile(user=self.user, name="Existing User")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        form = response.context["form"]
        self.assertEqual(form.instance, existing_profile)                                       

    def test_get_no_temp_booking_uuid_in_session(self):
        """ Test GET request when temp_booking_uuid is not in the session. """
        session = self.client.session
        del session["temp_booking_uuid"]
        session.save()

        response = self.client.get(self.url, follow=False)                                         
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        
                                                       
        response_followed = self.client.get(self.url)                                 
        messages_list = list(get_messages(response_followed.wsgi_request))
        self.assertTrue(any("Your booking session has expired." in str(m) for m in messages_list))


    def test_get_invalid_temp_booking_uuid_in_session(self):
        """ Test GET request with an invalid (non-UUID) temp_booking_uuid in session. """
        session = self.client.session
        session["temp_booking_uuid"] = "not-a-valid-uuid"
        session.save()

        response = self.client.get(self.url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        response_followed = self.client.get(self.url)
        messages_list = list(get_messages(response_followed.wsgi_request))
        self.assertTrue(any("Your booking session has expired." in str(m) for m in messages_list))

    def test_get_non_existent_temp_booking_uuid_in_session(self):
        """ Test GET request with a valid UUID in session that doesn't match any TempHireBooking. """
        session = self.client.session
        session["temp_booking_uuid"] = str(uuid.uuid4())                         
        session.save()

        response = self.client.get(self.url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        response_followed = self.client.get(self.url)
        messages_list = list(get_messages(response_followed.wsgi_request))
        self.assertTrue(any("Your booking session has expired." in str(m) for m in messages_list))

    @patch('hire.views.step4_HasAccount_view.calculate_booking_grand_total')
    def test_post_invalid_data_renders_form_with_errors(self, mock_calculate_total):
        """ Test POST with invalid data, expecting the form to be re-rendered with errors. """
        post_data_fields, post_data_files = self._get_valid_australian_driver_data()
        del post_data_fields['name']                    

        response = self.client.post(self.url, data=post_data_fields, files=post_data_files)
        self.assertEqual(response.status_code, 200)                            
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertTrue(form.errors)
        self.assertIn('name', form.errors)                                    

        messages_list = list(get_messages(response.wsgi_request))
                                                                                 
        self.assertTrue(any("Please correct the errors below (form validation)." in str(m) for m in messages_list))
        
        mock_calculate_total.assert_not_called()                                                      

    def test_post_no_temp_booking_uuid_in_session(self):
        """ Test POST when temp_booking_uuid is not in session. """
        session = self.client.session
        del session["temp_booking_uuid"]
        session.save()

        post_data_fields, post_data_files = self._get_valid_australian_driver_data()
        response = self.client.post(self.url, data=post_data_fields, files=post_data_files, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        
        response_followed = self.client.post(self.url, data=post_data_fields, files=post_data_files)
        messages_list = list(get_messages(response_followed.wsgi_request))
        self.assertTrue(any("Your booking session has expired." in str(m) for m in messages_list))
