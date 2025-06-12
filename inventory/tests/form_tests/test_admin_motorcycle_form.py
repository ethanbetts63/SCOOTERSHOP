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

    def test_form_fields_and_widgets(self):
        form = MotorcycleForm()
        expected_fields = [
            'conditions', 'brand', 'model', 'year', 'price',
            'odometer', 'engine_size', 'seats', 'transmission',
            'daily_hire_rate', 'hourly_hire_rate', 'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number',
            'vin_number', 'engine_number',
        ]
        self.assertEqual(list(form.fields.keys()), expected_fields)

        self.assertIsInstance(form.fields['hourly_hire_rate'].widget, forms.NumberInput)
        self.assertEqual(form.fields['hourly_hire_rate'].widget.attrs['step'], '0.01')
        self.assertIsInstance(form.fields['rego_exp'].widget, forms.DateInput)
        self.assertEqual(form.fields['rego_exp'].widget.input_type, 'date')
        self.assertIsInstance(form.fields['conditions'].widget, forms.CheckboxSelectMultiple)
        self.assertIn('condition-checkbox-list', form.fields['conditions'].widget.attrs['class'])
        self.assertIsInstance(form.fields['daily_hire_rate'].widget, forms.NumberInput)
        self.assertEqual(form.fields['daily_hire_rate'].widget.attrs['step'], '0.01')
        self.assertIsInstance(form.fields['seats'].widget, forms.NumberInput)
        self.assertEqual(form.fields['seats'].widget.attrs['min'], '0')
        self.assertEqual(form.fields['seats'].widget.attrs['max'], '3')
        self.assertIsInstance(form.fields['transmission'].widget, forms.Select)
        self.assertIn('form-control', form.fields['transmission'].widget.attrs['class'])
        self.assertIsInstance(form.fields['engine_size'], forms.IntegerField)
        self.assertEqual(form.fields['engine_size'].min_value, 0)
        self.assertIsInstance(form.fields['odometer'], forms.IntegerField)
        self.assertEqual(form.fields['odometer'].min_value, 0)


    def test_init_method_required_fields(self):
        form = MotorcycleForm()
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

    def test_clean_method_engine_size_validation(self):
        data_negative_engine = {
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': -10, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [],
        }
        form = MotorcycleForm(data=data_negative_engine)
        self.assertFalse(form.is_valid())
        self.assertIn('engine_size', form.errors)
        self.assertIn("Ensure this value is greater than or equal to 0.", form.errors['engine_size'])

    def test_clean_method_odometer_validation(self):
        data_negative_odometer = {
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': -50, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [],
        }
        form = MotorcycleForm(data=data_negative_odometer)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        self.assertIn("Ensure this value is greater than or equal to 0.", form.errors['odometer'])

    def test_clean_method_rego_uppercase(self):
        data_rego = {
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
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [self.condition_new.pk, self.condition_used.pk],
        }
        form = MotorcycleForm(data=data_new_and_used)
        self.assertFalse(form.is_valid())
        self.assertIn('conditions', form.errors)
        self.assertIn("A motorcycle with 'New' condition cannot have other conditions.", form.errors['conditions'])

    def test_clean_method_conditions_demo_exclusive(self):
        data_demo_and_used = {
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [self.condition_demo.pk, self.condition_used.pk],
        }
        form = MotorcycleForm(data=data_demo_and_used)
        self.assertFalse(form.is_valid())
        self.assertIn('conditions', form.errors)
        self.assertIn("A motorcycle with 'Demo' condition cannot have other conditions.", form.errors['conditions'])

    def test_clean_method_conditions_multiple_valid(self):
        data_multiple_valid = {
            'brand': 'Honda', 'model': 'CBR', 'year': 2020,
            'engine_size': 500, 'odometer': 1000, 'is_available': True,
            'transmission': 'automatic', 'stock_number': 'STK001',
            'conditions': [self.condition_used.pk],
        }
        form = MotorcycleForm(data=data_multiple_valid)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_save_method_title_generation(self):
        data_full = {
            'brand': 'Yamaha',
            'model': 'MT-07',
            'year': 2023,
            'engine_size': 700,
            'odometer': 50,
            'is_available': True,
            'transmission': 'manual',
            'stock_number': 'STK001',
            'conditions': [],
        }
        form = MotorcycleForm(data=data_full)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        motorcycle_instance = form.save(commit=False)
        self.assertEqual(motorcycle_instance.title, '2023 Yamaha Mt-07')

        motorcycle_instance.save()
        form.save_m2m()
        self.assertIsNotNone(motorcycle_instance.pk)
        self.assertEqual(motorcycle_instance.title, '2023 Yamaha Mt-07')

        # data for 'Untitled Motorcycle' scenario - now requires brand, model, year, transmission, stock_number
        data_no_details = {
            'brand': 'Generic',
            'model': 'Bike',
            'year': 2000,
            'engine_size': 100,
            'odometer': 0,
            'is_available': True,
            'transmission': 'manual',
            'stock_number': 'STK002',
            'conditions': [],
        }
        form_no_details = MotorcycleForm(data=data_no_details)
        self.assertTrue(form_no_details.is_valid(), form_no_details.errors.as_json())
        motorcycle_no_details = form_no_details.save(commit=False)
        # Expected title should now reflect provided required fields
        self.assertEqual(motorcycle_no_details.title, '2000 Generic Bike')
        motorcycle_no_details.save()
        form_no_details.save_m2m()
        self.assertIsNotNone(motorcycle_no_details.pk)

    def test_form_with_valid_data(self):
        data = {
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

    def test_form_with_invalid_data(self):
        data = {
            # Missing required fields to trigger validation errors
            'brand': '',
            'model': '',
            'year': None,
            'transmission': '',
            'stock_number': '',
            'engine_size': -50,
            'odometer': -100,
            'is_available': True,
            'conditions': [],
        }
        form = MotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('engine_size', form.errors)
        self.assertIn('odometer', form.errors)
        self.assertIn('brand', form.errors)
        self.assertIn('model', form.errors)
        self.assertIn('transmission', form.errors)
        self.assertIn('stock_number', form.errors)

