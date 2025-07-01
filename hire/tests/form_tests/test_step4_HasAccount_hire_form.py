                                                          

from django.test import TestCase
from django.core.exceptions import ValidationError
import datetime
from django.utils import timezone
from unittest.mock import MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile                            

from hire.forms.step4_HasAccount_form import Step4HasAccountForm
from hire.tests.test_helpers.model_factories import create_driver_profile, create_temp_hire_booking

class Step4HasAccountFormTests(TestCase):
    """
    Tests for the Step4HasAccountForm, focusing on its clean method.
    """

    def setUp(self):
        """
        Set up common data for tests.
        """
        self.return_date_future = timezone.now().date() + datetime.timedelta(days=30)
        self.return_date_past = timezone.now().date() - datetime.timedelta(days=30)

                                             
        self.temp_booking_future_return = MagicMock()
        self.temp_booking_future_return.return_date = self.return_date_future

        self.temp_booking_past_return = MagicMock()
        self.temp_booking_past_return.return_date = self.return_date_past

                                                      
        self.dummy_license = SimpleUploadedFile("license.jpg", b"file_content", content_type="image/jpeg")
        self.dummy_int_license = SimpleUploadedFile("int_license.jpg", b"file_content", content_type="image/jpeg")
        self.dummy_passport = SimpleUploadedFile("passport.jpg", b"file_content", content_type="image/jpeg")

                                                                    
                                                                                   
        self.existing_driver_profile = create_driver_profile(
            name="Existing User",
            email="existing@example.com",
            is_australian_resident=True,
            license_photo=self.dummy_license,                         
            license_number='EX12345678',
            license_expiry_date=timezone.now().date() + datetime.timedelta(days=100),
            international_license_photo=None,                                
            passport_photo=None,                                
        )

                                                                 
        self.base_australian_data = {
            'name': 'Jane Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '0412345678',
            'address_line_1': '100 Main St',
            'city': 'Melbourne',
            'country': 'Australia',
            'date_of_birth': datetime.date(1990, 1, 1),
            'is_australian_resident': 'True',
            'license_number': 'AUS12345',
            'license_expiry_date': self.return_date_future + datetime.timedelta(days=1),
            'license_photo': self.dummy_license,                         
                                                                                                     
            'international_license_photo': None,
            'international_license_issuing_country': '',
            'international_license_expiry_date': None,
            'passport_photo': None,                                    
            'passport_number': '',
            'passport_expiry_date': None,
        }

                                                             
        self.base_foreign_data = {
            'name': 'John Foreigner',
            'email': 'john.f@example.com',
            'phone_number': '0123456789',
            'address_line_1': '10 International Blvd',
            'city': 'Sydney',
            'country': 'USA',
            'date_of_birth': datetime.date(1985, 5, 10),
            'is_australian_resident': 'False',
            'international_license_photo': self.dummy_int_license,                         
            'international_license_issuing_country': 'USA',
            'international_license_expiry_date': self.return_date_future + datetime.timedelta(days=1),
            'passport_photo': self.dummy_passport,                         
            'passport_number': 'P1234567',
            'passport_expiry_date': self.return_date_future + datetime.timedelta(days=1),
                                                                                    
            'license_number': '',
            'license_expiry_date': None,
            'id_image': None,
            'international_id_image': None,
        }


                                       
    def test_clean_valid_australian_resident(self):
        """
        Test a valid submission for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
        form = Step4HasAccountForm(data=form_data, files={
            'license_photo': self.dummy_license                         
        }, temp_booking=self.temp_booking_future_return)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['is_australian_resident'], True)

    def test_clean_valid_australian_resident_with_existing_photo(self):
        """
        Test a valid submission for an Australian resident when license photo already exists on instance.
        """
        form_data = self.base_australian_data.copy()
        form_data['license_photo'] = None                                                 
        form = Step4HasAccountForm(
            data=form_data,
            instance=self.existing_driver_profile,                              
            temp_booking=self.temp_booking_future_return
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['is_australian_resident'], True)

    def test_clean_australian_resident_missing_license_photo(self):
        """
        Test missing license photo for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
                                                                         
        fresh_profile = create_driver_profile(license_photo=None, is_australian_resident=True)                                    
        form = Step4HasAccountForm(data=form_data, instance=fresh_profile, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_photo', form.errors)
        self.assertIn("Australian residents must upload their domestic driver's license photo.", form.errors['license_photo'])

    def test_clean_australian_resident_missing_license_number(self):
        """
        Test missing license number for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
        form_data['license_number'] = ''                     
        form = Step4HasAccountForm(data=form_data, files={
            'license_photo': self.dummy_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_number', form.errors)
        self.assertIn("Australian residents must provide their domestic license number.", form.errors['license_number'])

    def test_clean_australian_resident_license_expired_before_return(self):
        """
        Test Australian license expiry date before return date.
        """
        form_data = self.base_australian_data.copy()
        form_data['license_expiry_date'] = self.return_date_future - datetime.timedelta(days=1)                     
        form = Step4HasAccountForm(data=form_data, files={
            'license_photo': self.dummy_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_expiry_date', form.errors)
        self.assertIn("Your Australian Driver's License must not expire before the end of your booking.", form.errors['license_expiry_date'])

                                    
    def test_clean_valid_foreign_resident(self):
        """
        Test a valid submission for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['is_australian_resident'], False)

    def test_clean_foreign_resident_missing_international_license_photo(self):
        """
        Test missing international license photo for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        fresh_profile = create_driver_profile(international_license_photo=None, is_australian_resident=False)
        form = Step4HasAccountForm(data=form_data, instance=fresh_profile, files={
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_photo', form.errors)
        self.assertIn("Foreign drivers must upload their International Driver's License photo.", form.errors['international_license_photo'])

    def test_clean_foreign_resident_missing_passport_photo(self):
        """
        Test missing passport photo for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        fresh_profile = create_driver_profile(passport_photo=None, is_australian_resident=False)
        form = Step4HasAccountForm(data=form_data, instance=fresh_profile, files={
            'international_license_photo': self.dummy_int_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_photo', form.errors)
        self.assertIn("Foreign drivers must upload their passport photo.", form.errors['passport_photo'])

    def test_clean_foreign_resident_missing_international_license_country(self):
        """
        Test missing international license issuing country for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['international_license_issuing_country'] = ''                     
        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_issuing_country', form.errors)
        self.assertIn("Foreign drivers must provide the issuing country of their International Driver's License.", form.errors['international_license_issuing_country'])

    def test_clean_foreign_resident_missing_international_license_expiry_date(self):
        """
        Test missing international license expiry date for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['international_license_expiry_date'] = None                     
        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_expiry_date', form.errors)
        self.assertIn("Foreign drivers must provide the expiry date of their International Driver's License.", form.errors['international_license_expiry_date'])

    def test_clean_foreign_resident_international_license_expired_before_return(self):
        """
        Test international license expiry date before return date.
        """
        form_data = self.base_foreign_data.copy()
        form_data['international_license_expiry_date'] = self.return_date_future - datetime.timedelta(days=1)                     
        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_expiry_date', form.errors)
        self.assertIn("Your International Driver's License must not expire before the end of your booking.", form.errors['international_license_expiry_date'])

    def test_clean_foreign_resident_missing_passport_number(self):
        """
        Test missing passport number for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['passport_number'] = ''                     
        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_number', form.errors)
        self.assertIn("Foreign drivers must provide their passport number.", form.errors['passport_number'])

    def test_clean_foreign_resident_missing_passport_expiry_date(self):
        """
        Test missing passport expiry date for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['passport_expiry_date'] = None                     
        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_expiry_date', form.errors)
        self.assertIn("Foreign drivers must provide their passport expiry date.", form.errors['passport_expiry_date'])

    def test_clean_foreign_resident_passport_expired_before_return(self):
        """
        Test passport expiry date before return date.
        """
        form_data = self.base_foreign_data.copy()
        form_data['passport_expiry_date'] = self.return_date_future - datetime.timedelta(days=1)                     
                                                                                         
        form_data['international_license_issuing_country'] = 'USA'                         
        form_data['international_license_expiry_date'] = self.return_date_future + datetime.timedelta(days=1)                       
        form_data['passport_number'] = 'P1234567'                         

        form = Step4HasAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_expiry_date', form.errors)
        self.assertIn("Your passport must not expire before the end of your booking.", form.errors['passport_expiry_date'])

