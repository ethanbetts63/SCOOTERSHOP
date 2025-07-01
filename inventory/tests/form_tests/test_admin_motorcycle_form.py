from django.test import TestCase
from django import forms
import datetime
from inventory.models import Motorcycle, MotorcycleCondition
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory


class MotorcycleFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')
        cls.condition_demo = MotorcycleConditionFactory(name='demo', display_name='Demo')
        cls.motorcycle = MotorcycleFactory()


    def test_init_method_required_fields(self):
        form = MotorcycleForm()
        self.assertTrue(form.fields['status'].required)                                
        self.assertFalse(form.fields['price'].required)
        self.assertFalse(form.fields['daily_hire_rate'].required)
        self.assertFalse(form.fields['hourly_hire_rate'].required)
        self.assertFalse(form.fields['description'].required)
        self.assertFalse(form.fields['seats'].required)
        self.assertTrue(form.fields['transmission'].required)
        self.assertFalse(form.fields['rego'].required)
        self.assertFalse(form.fields['rego_exp'].required)
        self.assertTrue(form.fields['stock_number'].required)
        self.assertTrue(form.fields['brand'].required)
        self.assertTrue(form.fields['model'].required)
        self.assertTrue(form.fields['year'].required)
        self.assertFalse(form.fields['vin_number'].required)
        self.assertFalse(form.fields['engine_number'].required)


    def test_clean_method_brand_and_model_capitalization(self):
        data = {
            'status': 'for_sale',                      
            'brand': 'honda',
            'model': 'cbr500r',
            'year': 2020,
            'engine_size': 500,
            'odometer': 1000,
            'is_available': True,
            'transmission': 'automatic',
            'stock_number': 'STK001',
            'conditions': [],
        }
        form = MotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data['brand'], 'Honda')
        self.assertEqual(cleaned_data['model'], 'Cbr500r')

    def test_clean_method_year_validation(self):
        current_year = datetime.date.today().year

        base_data = {
            'status': 'for_sale',                      
            'brand': 'Honda', 'model': 'CBR',
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [],
        }

        data_invalid_low_year = base_data.copy()
        data_invalid_low_year['year'] = 1884
        form = MotorcycleForm(data=data_invalid_low_year)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn(f"Please enter a valid year between 1885 and {current_year + 2}.", form.errors['year'])

        data_invalid_high_year = base_data.copy()
        data_invalid_high_year['year'] = current_year + 3
        form = MotorcycleForm(data=data_invalid_high_year)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn(f"Please enter a valid year between 1885 and {current_year + 2}.", form.errors['year'])

        data_valid_year = base_data.copy()
        data_valid_year['year'] = 2020
        form = MotorcycleForm(data=data_valid_year)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_clean_method_rego_uppercase(self):
        data_rego = {
            'status': 'for_sale',                      
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'rego': 'abc123',
            'conditions': [],
        }
        form = MotorcycleForm(data=data_rego)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data['rego'], 'ABC123')

    def test_clean_method_conditions_new_exclusive(self):
        data_new_and_used = {
            'status': 'for_sale',                      
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [self.condition_new.pk, self.condition_used.pk],
            'quantity': 1,
        }
        form = MotorcycleForm(data=data_new_and_used)
        self.assertFalse(form.is_valid())
        self.assertIn('conditions', form.errors)
        self.assertIn("A motorcycle with 'New' condition cannot have other conditions.", form.errors['conditions'])

    def test_clean_method_conditions_demo_exclusive(self):
        data_demo_and_used = {
            'status': 'for_sale',                      
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [self.condition_demo.pk, self.condition_used.pk],
            'quantity': 1,
        }
        form = MotorcycleForm(data=data_demo_and_used)
        self.assertFalse(form.is_valid())
        self.assertIn('conditions', form.errors)
        self.assertIn("A motorcycle with 'Demo' condition cannot have other conditions.", form.errors['conditions'])

    def test_clean_method_conditions_multiple_valid(self):
        data_multiple_valid = {
            'status': 'for_sale',                      
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [self.condition_used.pk],
            'quantity': 1,
        }
        form = MotorcycleForm(data=data_multiple_valid)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_save_method_title_generation(self):
        data_full = {
            'status': 'for_sale',                      
            'brand': 'Yamaha',
            'model': 'MT-07',
            'year': 2023,
            'engine_size': 700,
            'odometer': 50,
            'is_available': True,
            'transmission': 'manual',
            'stock_number': 'STK001',
            'conditions': [],
            'quantity': 1,
        }
        form = MotorcycleForm(data=data_full)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        motorcycle_instance = form.save(commit=False)
        self.assertEqual(motorcycle_instance.title, '2023 Yamaha Mt-07')

        motorcycle_instance.save()
        form.save_m2m()
        self.assertIsNotNone(motorcycle_instance.pk)
        self.assertEqual(motorcycle_instance.title, '2023 Yamaha Mt-07')

        data_no_details = {
            'status': 'for_sale',                      
            'brand': 'Generic',
            'model': 'Bike',
            'year': 2000,
            'engine_size': 100,
            'odometer': 0,
            'is_available': True,
            'transmission': 'manual',
            'stock_number': 'STK002',
            'conditions': [],
            'quantity': 1,
        }
        form_no_details = MotorcycleForm(data=data_no_details)
        self.assertTrue(form_no_details.is_valid(), form_no_details.errors.as_json())
        motorcycle_no_details = form_no_details.save(commit=False)
        self.assertEqual(motorcycle_no_details.title, '2000 Generic Bike')
        motorcycle_no_details.save()
        form_no_details.save_m2m()
        self.assertIsNotNone(motorcycle_no_details.pk)

    def test_form_with_valid_data(self):
        data = {
            'status': 'for_sale',                      
            'conditions': [self.condition_new.pk],
            'brand': 'Kawasaki',
            'model': 'Ninja 400',
            'year': 2022,
            'price': 8000.00,
            'odometer': 1500,
            'engine_size': 400,
            'seats': 2,
            'transmission': 'manual',
            'daily_hire_rate': 100.00,
            'hourly_hire_rate': 20.00,
            'description': 'A fantastic sportbike.',
            'is_available': True,
            'rego': 'XYZ789',
            'rego_exp': '2025-12-31',
            'stock_number': 'KWI001',
            'vin_number': 'VINTEST123',
            'engine_number': 'ENG456',
            'quantity': 1,
        }
        form = MotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        motorcycle = form.save()
        self.assertIsNotNone(motorcycle.pk)
        self.assertEqual(motorcycle.brand, 'Kawasaki')
        self.assertEqual(motorcycle.model, 'Ninja 400')
        self.assertEqual(motorcycle.year, 2022)
        self.assertEqual(motorcycle.title, '2022 Kawasaki Ninja 400')
        self.assertIn(self.condition_new, motorcycle.conditions.all())
        self.assertEqual(motorcycle.vin_number, 'VINTEST123')
        self.assertEqual(motorcycle.engine_number, 'ENG456')
        self.assertEqual(motorcycle.quantity, 1)

                                  

    def test_form_saves_is_available_correctly(self):
        """Tests that the 'is_available' field is correctly saved."""
                                                 
        data_available = {
            'status': 'for_sale',
            'brand': 'Test', 'model': 'Available', 'year': 2022,
            'engine_size': 500, 'odometer': 100, 'transmission': 'manual',
            'stock_number': 'AV-001', 'conditions': [self.condition_used.pk],
            'is_available': True,
        }
        form_available = MotorcycleForm(data=data_available)
        self.assertTrue(form_available.is_valid(), form_available.errors.as_json())
        instance_available = form_available.save()
        self.assertTrue(instance_available.is_available, "Motorcycle should be saved as available.")
        self.assertEqual(instance_available.status, 'for_sale')


                                                   
                                                                                         
                                                                          
                                                                                    
                                                                    
        data_unavailable = {
            'status': 'unavailable',
            'brand': 'Test', 'model': 'Unavailable', 'year': 2022,
            'engine_size': 500, 'odometer': 100, 'transmission': 'manual',
            'stock_number': 'UN-001', 'conditions': [self.condition_used.pk],
        }                                                                   

        form_unavailable = MotorcycleForm(data=data_unavailable)

                                                                             
                                                                                        
        self.assertTrue(form_unavailable.is_valid(),
                        f"Form should be valid when 'is_available' is unchecked. Errors: {form_unavailable.errors.as_json()}")
        
        instance_unavailable = form_unavailable.save()
        self.assertFalse(instance_unavailable.is_available, "Motorcycle should be saved as not available.")
        self.assertEqual(instance_unavailable.status, 'unavailable')


    def test_form_saves_status_correctly(self):
        """Tests that the 'status' field is correctly saved."""
        base_data = {
            'brand': 'Test', 'model': 'Status', 'year': 2022,
            'engine_size': 500, 'odometer': 100, 'transmission': 'manual',
            'stock_number': 'ST-001', 'conditions': [self.condition_used.pk],
            'is_available': True,
        }

                            
        sold_data = base_data.copy()
        sold_data['status'] = 'sold'
        sold_data['stock_number'] = 'ST-002'                                  
        form_sold = MotorcycleForm(data=sold_data)
        self.assertTrue(form_sold.is_valid(), form_sold.errors.as_json())
        instance_sold = form_sold.save()
        self.assertEqual(instance_sold.status, 'sold')

                                
        reserved_data = base_data.copy()
        reserved_data['status'] = 'reserved'
        reserved_data['stock_number'] = 'ST-003'                      
        form_reserved = MotorcycleForm(data=reserved_data)
        self.assertTrue(form_reserved.is_valid(), form_reserved.errors.as_json())
        instance_reserved = form_reserved.save()
        self.assertEqual(instance_reserved.status, 'reserved')
