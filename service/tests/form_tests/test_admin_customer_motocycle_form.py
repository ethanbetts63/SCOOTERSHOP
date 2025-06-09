from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date

# Import the form and model to be tested
from service.forms import AdminCustomerMotorcycleForm
from service.models import CustomerMotorcycle

# Import factories for creating test data
from ..test_helpers.model_factories import ServiceProfileFactory, CustomerMotorcycleFactory

class AdminCustomerMotorcycleFormTest(TestCase):
    """
    Tests for the AdminCustomerMotorcycleForm.
    This form directly uses the CustomerMotorcycle model's clean method for most validations,
    so these tests cover both form and model-level validation.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.service_profile = ServiceProfileFactory(name="Test Service Profile")
        cls.valid_motorcycle_data = {
            'brand': 'Honda',
            'model': 'CBR1000RR',
            'year': date.today().year - 5, # A valid recent year
            'rego': 'ABC123',
            'odometer': 15000,
            'transmission': 'MANUAL',
            'engine_size': '1000cc',
            'vin_number': '1234567890ABCDEFG', # Corrected: 17 characters for valid VIN
            'engine_number': 'ENG12345',
            'service_profile': cls.service_profile.pk,
        }

    def test_form_valid_data_create(self):
        """
        Test that the form is valid with all correct data for creation.
        """
        data = self.valid_motorcycle_data.copy()
        form = AdminCustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")
        
        motorcycle = form.save()
        self.assertIsInstance(motorcycle, CustomerMotorcycle)
        self.assertEqual(motorcycle.brand, data['brand'])
        self.assertEqual(motorcycle.service_profile, self.service_profile)

    def test_form_valid_data_create_without_service_profile(self):
        """
        Test that the form is valid when creating a motorcycle without linking a ServiceProfile.
        """
        data = self.valid_motorcycle_data.copy()
        data['service_profile'] = '' # No service profile
        form = AdminCustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")
        
        motorcycle = form.save()
        self.assertIsNone(motorcycle.service_profile)

    def test_form_valid_data_update(self):
        """
        Test that the form is valid for updating an existing motorcycle.
        """
        existing_motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile)
        
        data = self.valid_motorcycle_data.copy()
        data['brand'] = 'Yamaha' # Change a field
        form = AdminCustomerMotorcycleForm(data=data, instance=existing_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

        motorcycle = form.save()
        self.assertEqual(motorcycle.pk, existing_motorcycle.pk) # Ensure it's the same instance
        self.assertEqual(motorcycle.brand, 'Yamaha')


    # --- Required Field Validations (from CustomerMotorcycle model's clean method) ---

    def test_missing_required_fields(self):
        """
        Test that the form catches missing required fields.
        """
        required_fields = ['brand', 'model', 'year', 'rego', 'odometer', 'transmission', 'engine_size']
        
        for field in required_fields:
            with self.subTest(field=field):
                invalid_data = self.valid_motorcycle_data.copy()
                if field == 'odometer':
                    invalid_data[field] = None # Odometer specifically checks for None
                else:
                    invalid_data[field] = '' # Empty string for char/int fields
                
                form = AdminCustomerMotorcycleForm(data=invalid_data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
                
                # Adjust expected error message based on field and potential Django default validation
                if field == 'rego':
                    expected_error_message = "Motorcycle registration is required."
                elif field == 'odometer':
                    expected_error_message = "Motorcycle odometer is required."
                elif field == 'transmission':
                    expected_error_message = "Motorcycle transmission type is required."
                elif field == 'year':
                    expected_error_message = "Motorcycle year is required."
                else:
                    expected_error_message = f"Motorcycle {field.replace('_', ' ')} is required."

                # Verify the presence of the expected message
                self.assertIn(expected_error_message, form.errors[field])


    # --- Specific Model-Level Validations ---

    def test_motorcycle_year_validation(self):
        """
        Test year validation: cannot be in the future, cannot be too old.
        And also test the widget's min attribute validation.
        """
        current_year = date.today().year

        # Test future year (model's clean)
        data_future_year = self.valid_motorcycle_data.copy()
        data_future_year['year'] = current_year + 1
        form = AdminCustomerMotorcycleForm(data=data_future_year)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Motorcycle year cannot be in the future.', form.errors['year'])

        # Test very old year (model's clean - e.g., current year 2025, 100 years ago is 1925, so 1924 is too old)
        data_old_year = self.valid_motorcycle_data.copy()
        data_old_year['year'] = current_year - 101 
        form = AdminCustomerMotorcycleForm(data=data_old_year)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Motorcycle year seems too old. Please check the year.', form.errors['year'])

        # Test year 0: Model's clean will catch this as 'required' because 0 evaluates to False
        data_zero_year = self.valid_motorcycle_data.copy()
        data_zero_year['year'] = 0
        form = AdminCustomerMotorcycleForm(data=data_zero_year)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Motorcycle year is required.', form.errors['year'])

        # Test year below widget's min (1900) but within model's 'too old' threshold.
        # The model's validation is likely to take precedence here.
        # Example: if current_year = 2025, current_year - 100 = 1925.
        # Year = 1899 is < 1925, so model's 'too old' will be hit.
        data_below_widget_min = self.valid_motorcycle_data.copy()
        data_below_widget_min['year'] = 1899
        form = AdminCustomerMotorcycleForm(data=data_below_widget_min)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        # Expect the model's error for years falling under the 'too old' condition
        self.assertIn('Motorcycle year seems too old. Please check the year.', form.errors['year'])


    def test_vin_number_length_validation(self):
        """
        Test VIN number length validation.
        - Must be 17 characters if provided.
        - Max length (17) handled by Django's CharField validation if too long.
        """
        # Too short (model's clean)
        data_short_vin = self.valid_motorcycle_data.copy()
        data_short_vin['vin_number'] = 'SHORTVIN' # 8 chars
        form = AdminCustomerMotorcycleForm(data=data_short_vin)
        self.assertFalse(form.is_valid())
        self.assertIn('vin_number', form.errors)
        self.assertIn('VIN number must be 17 characters long.', form.errors['vin_number'])

        # Too long (Django's CharField max_length validation)
        data_long_vin = self.valid_motorcycle_data.copy()
        data_long_vin['vin_number'] = 'TOOLONGVINNUMBERXXY' # 19 chars
        form = AdminCustomerMotorcycleForm(data=data_long_vin)
        self.assertFalse(form.is_valid())
        self.assertIn('vin_number', form.errors)
        # Django's default CharField max_length validation message
        self.assertIn('Ensure this value has at most 17 characters (it has 19).', form.errors['vin_number'])

        # Correct length should be valid
        data_correct_vin = self.valid_motorcycle_data.copy()
        data_correct_vin['vin_number'] = 'THISISAVALIDVIN17' # 17 chars
        form = AdminCustomerMotorcycleForm(data=data_correct_vin)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")

        # Empty VIN should be valid (because it's blank=True, null=True)
        data_empty_vin = self.valid_motorcycle_data.copy()
        data_empty_vin['vin_number'] = ''
        form = AdminCustomerMotorcycleForm(data=data_empty_vin)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_json()}")


    def test_odometer_negative_validation(self):
        """
        Test that odometer reading cannot be negative.
        This is caught by PositiveIntegerField and the widget's min attribute.
        """
        data_negative_odometer = self.valid_motorcycle_data.copy()
        data_negative_odometer['odometer'] = -100
        form = AdminCustomerMotorcycleForm(data=data_negative_odometer)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        # Django's default PositiveIntegerField validator or widget min will produce this
        self.assertIn('Ensure this value is greater than or equal to 0.', form.errors['odometer'])

    def test_transmission_choices(self):
        """
        Test that transmission field only accepts valid choices.
        """
        data_invalid_transmission = self.valid_motorcycle_data.copy()
        data_invalid_transmission['transmission'] = 'INVALID_TYPE'
        form = AdminCustomerMotorcycleForm(data=data_invalid_transmission)
        self.assertFalse(form.is_valid())
        self.assertIn('transmission', form.errors)
        self.assertIn("Select a valid choice. INVALID_TYPE is not one of the available choices.", form.errors['transmission'])


    def test_service_profile_queryset(self):
        """
        Test that the service_profile queryset is ordered correctly.
        """
        profile_a = ServiceProfileFactory(name="Profile A", email="a@example.com")
        profile_b = ServiceProfileFactory(name="Profile B", email="b@example.com")
        profile_c = ServiceProfileFactory(name="Profile C", email="c@example.com")
        
        form = AdminCustomerMotorcycleForm()
        # The queryset from ModelChoiceField already returns ordered objects.
        queryset = list(form.fields['service_profile'].queryset)
        
        # Collect all service profiles, including the one from setUpTestData
        all_profiles = [self.service_profile, profile_a, profile_b, profile_c]
        # Sort them manually based on the expected order (name, then email)
        expected_order = sorted(all_profiles, key=lambda p: (p.name, p.email))

        # Assert that the queryset matches the expected order
        self.assertListEqual(queryset, expected_order)

