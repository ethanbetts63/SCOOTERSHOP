from django.test import TestCase
from service.models import CustomerMotorcycle, ServiceProfile                        
from service.utils.admin_process_customer_motorcycle_form import admin_process_customer_motorcycle_form
from ..test_helpers.model_factories import ServiceProfileFactory, CustomerMotorcycleFactory, ServiceBrandFactory

class AdminProcessCustomerMotorcycleFormTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.service_profile = ServiceProfileFactory()
        cls.another_service_profile = ServiceProfileFactory()                      
        cls.service_brand_honda = ServiceBrandFactory(name='Honda')
        cls.service_brand_yamaha = ServiceBrandFactory(name='Yamaha')

    def test_create_new_motorcycle_with_existing_brand(self):
        
        post_data = {
            'service_profile': self.service_profile.pk,                            
            'brand': self.service_brand_honda.name,
            'model': 'CBR500R',
            'year': 2022,
            'engine_size': '500cc',
            'rego': 'ABC123',
            'odometer': 1500,
            'transmission': 'MANUAL',
            'vin_number': '12345678901234567',
            'engine_number': 'ENG12345',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile                                                              
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(motorcycle_instance)
        self.assertEqual(motorcycle_instance.service_profile, self.service_profile)
        self.assertEqual(motorcycle_instance.brand, post_data['brand'])
        self.assertEqual(motorcycle_instance.model, post_data['model'])
        self.assertEqual(motorcycle_instance.year, post_data['year'])
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)


    def test_create_new_motorcycle_with_custom_brand_typed_in(self):
        
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': 'Custom Chopper Brand',                            
            'model': 'Custom Build 1',
            'year': 2023,
            'engine_size': '1800cc',
            'rego': 'XYZ789',
            'odometer': 500,
            'transmission': 'MANUAL',
            'vin_number': 'ABCDEFGHIJKLMNOPQ',
            'engine_number': 'CUSTENG001',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(motorcycle_instance)
        self.assertEqual(motorcycle_instance.service_profile, self.service_profile)
                                                            
        self.assertEqual(motorcycle_instance.brand, post_data['brand'])
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)


    def test_update_existing_motorcycle_change_brand(self):
        
        initial_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.service_brand_honda.name,
            model='Old Model',
            year=2010,
            rego='OLD111',
            odometer=50000,
            transmission='MANUAL',
        )
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

                                                                             
        updated_post_data = {
            'service_profile': self.service_profile.pk,                              
            'brand': self.service_brand_yamaha.name,
            'model': 'FZ-07',
            'year': 2018,
            'engine_size': '689cc',
            'rego': 'NEW222',
            'odometer': 20000,
            'transmission': 'MANUAL',
            'vin_number': initial_motorcycle.vin_number,
            'engine_number': initial_motorcycle.engine_number,
        }
        files_data = {}

        form, updated_motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=updated_post_data,
            request_files=files_data,
            profile_instance=self.service_profile,
            motorcycle_id=initial_motorcycle.pk
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(updated_motorcycle_instance)
        self.assertEqual(updated_motorcycle_instance.pk, initial_motorcycle.pk)
        self.assertEqual(updated_motorcycle_instance.brand, updated_post_data['brand'])
        self.assertEqual(updated_motorcycle_instance.model, updated_post_data['model'])
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

    def test_update_existing_motorcycle_change_profile(self):
        
        initial_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand='Kawasaki',
            model='Ninja',
            year=2020,
            rego='OLDPROF',
            odometer=10000,
            transmission='MANUAL',
        )
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

        updated_post_data = {
            'service_profile': self.another_service_profile.pk,                        
            'brand': 'Kawasaki',                  
            'model': 'Ninja',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'NEWPROF',
            'odometer': 10500,
            'transmission': 'MANUAL',
            'vin_number': initial_motorcycle.vin_number,
            'engine_number': initial_motorcycle.engine_number,
        }
        files_data = {}

        form, updated_motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=updated_post_data,
            request_files=files_data,
            profile_instance=self.service_profile,                                                    
            motorcycle_id=initial_motorcycle.pk
        )

        self.assertTrue(form.is_valid())
        self.assertIsNotNone(updated_motorcycle_instance)
        self.assertEqual(updated_motorcycle_instance.pk, initial_motorcycle.pk)
        self.assertEqual(updated_motorcycle_instance.service_profile, self.another_service_profile)
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)


    def test_form_invalid_missing_required_fields(self):
        
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
                                
            'year': 2022,
            'engine_size': '500cc',
            'rego': 'ABC123',
            'odometer': 1500,
            'transmission': 'MANUAL',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('model', form.errors)                                              
        self.assertIsNone(motorcycle_instance)
        self.assertEqual(CustomerMotorcycle.objects.count(), 0)

    def test_form_invalid_year_in_future(self):
        
        from datetime import date
        future_year = date.today().year + 1

        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'Time Machine',
            'year': future_year,              
            'engine_size': '1000cc',
            'rego': 'FUTURA',
            'odometer': 0,
            'transmission': 'MANUAL',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIsNone(motorcycle_instance)

    def test_form_invalid_vin_number_length(self):
        
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'Short VIN',
            'year': 2020,
            'engine_size': '500cc',
            'rego': 'SHORTY',
            'odometer': 1000,
            'transmission': 'MANUAL',
            'vin_number': 'TOO_SHORT',                     
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('vin_number', form.errors)
        self.assertIsNone(motorcycle_instance)

    def test_form_invalid_negative_odometer(self):
        
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'Negative Odometer',
            'year': 2020,
            'engine_size': '500cc',
            'rego': 'NEGATIV',
            'odometer': -100,                    
            'transmission': 'MANUAL',
        }
        files_data = {}

        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile
        )

        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        self.assertIsNone(motorcycle_instance)

    def test_motorcycle_instance_not_found_with_form_error(self):
        
        post_data = {
            'service_profile': self.service_profile.pk,
            'brand': self.service_brand_honda.name,
            'model': 'NotFound',
            'year': 2020,
            'engine_size': '500cc',
            'rego': 'NOTFOUND',
            'odometer': 1000,
            'transmission': 'MANUAL',
        }
        files_data = {}

                                                 
        form, motorcycle_instance = admin_process_customer_motorcycle_form(
            request_post_data=post_data,
            request_files=files_data,
            profile_instance=self.service_profile,
            motorcycle_id=99999                    
        )

                                                                                   
        self.assertFalse(form.is_valid())
        self.assertIn('Selected motorcycle not found.', form.non_field_errors())
        self.assertIsNone(motorcycle_instance)
                                              
        self.assertEqual(CustomerMotorcycle.objects.count(), 0)

