from django.test import TestCase
from service.forms import ServiceBookingUserForm
from ..test_helpers.model_factories import ServiceProfileFactory

class ServiceBookingUserFormTest(TestCase):
    """
    Tests for the ServiceBookingUserForm (Step 4 form).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create a ServiceProfile instance using the factory for valid data.
        """
        cls.valid_service_profile_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone_number': '+61412345678',
            'address_line_1': '123 Main St',
            'address_line_2': '', # Explicitly set to empty string for testing form behavior
            'city': 'Sydney',
            'state': '', # Explicitly set to empty string for testing form behavior
            'post_code': '2000',
            'country': 'AU',
        }

    def test_form_valid_data(self):
        """
        Test that the form is valid with correct data.
        """
        form = ServiceBookingUserForm(data=self.valid_service_profile_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        # Ensure the cleaned data matches the input data
        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data['name'], 'John Doe')
        self.assertEqual(cleaned_data['email'], 'john.doe@example.com')
        self.assertEqual(cleaned_data['phone_number'], '+61412345678')
        self.assertEqual(cleaned_data['address_line_1'], '123 Main St')
        # For blank=True, null=True fields, Django's forms often clean empty strings to None
        self.assertIsNone(cleaned_data['address_line_2'])
        self.assertEqual(cleaned_data['city'], 'Sydney')
        # For blank=True, null=True fields, Django's forms often clean empty strings to None
        self.assertIsNone(cleaned_data['state'])
        self.assertEqual(cleaned_data['post_code'], '2000')
        self.assertEqual(cleaned_data['country'], 'AU')

    def test_form_invalid_data_missing_required_fields(self):
        """
        Test that the form is invalid if required fields are missing.
        'name', 'email', 'phone_number', 'address_line_1', 'city', 'post_code', 'country' are required.
        """
        required_fields = ['name', 'email', 'phone_number', 'address_line_1', 'city', 'post_code', 'country']

        for field in required_fields:
            with self.subTest(f"Missing field: {field}"):
                data = self.valid_service_profile_data.copy()
                data[field] = ''  # Set required field to empty
                form = ServiceBookingUserForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
                self.assertIn('This field is required.', form.errors[field])

    def test_form_invalid_email_format(self):
        """
        Test that the form is invalid with an incorrectly formatted email address.
        """
        data = self.valid_service_profile_data.copy()
        data['email'] = 'invalid-email'  # Invalid email format
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('Enter a valid email address.', form.errors['email'])

        data['email'] = 'user@.com'  # Invalid email format
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('Enter a valid email address.', form.errors['email'])

    def test_form_invalid_phone_number_format(self):
        """
        Test that the form is invalid with an incorrectly formatted phone number.
        The ServiceProfile model's clean method has a regex for phone numbers.
        """
        data = self.valid_service_profile_data.copy()

        # Define the exact expected error message from the ServiceProfile model's clean method
        expected_error_message = "Phone number must contain only digits, spaces, hyphens, and an optional leading '+'. Example: '+61412345678' or '0412 345 678'."

        # Test with non-digit characters (excluding +, spaces, hyphens)
        data['phone_number'] = 'abc1234567'
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
        self.assertIn(expected_error_message, form.errors['phone_number'])

        # Test with invalid characters
        data['phone_number'] = '0412!345678'
        form = ServiceBookingUserForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
        self.assertIn(expected_error_message, form.errors['phone_number'])

        # Test with valid but unusual format (should pass due to regex)
        data['phone_number'] = '0412 345-678' # Valid according to regex
        form = ServiceBookingUserForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid with valid phone: {form.errors}")
        self.assertEqual(form.cleaned_data['phone_number'], '0412 345-678')


    def test_form_with_existing_service_profile(self):
        """
        Test that the form can be initialized with an existing ServiceProfile instance
        and update it correctly.
        """
        existing_profile = ServiceProfileFactory(
            name='Jane Doe',
            email='jane.doe@example.com',
            phone_number='+61498765432',
            address_line_1='456 Oak Ave',
            address_line_2='Suite 100', # Ensure this is a string for the factory
            city='Melbourne',
            state='VIC', # Ensure this is a string for the factory
            post_code='3000',
            country='AU'
        )

        # Update some fields
        updated_data = {
            'name': 'Jane D. Smith',
            'email': 'jane.d.smith@example.com',
            'phone_number': '+61400111222',
            'address_line_1': '789 Pine Rd',
            'address_line_2': 'Apt 101',
            'city': 'Brisbane',
            'state': 'QLD',
            'post_code': '4000',
            'country': 'AU',
        }

        form = ServiceBookingUserForm(data=updated_data, instance=existing_profile)
        self.assertTrue(form.is_valid(), f"Form is not valid when updating instance: {form.errors}")

        # Save the form and check if the instance was updated
        updated_profile = form.save()
        self.assertEqual(updated_profile.name, 'Jane D. Smith')
        self.assertEqual(updated_profile.email, 'jane.d.smith@example.com')
        self.assertEqual(updated_profile.phone_number, '+61400111222')
        self.assertEqual(updated_profile.address_line_1, '789 Pine Rd')
        self.assertEqual(updated_profile.address_line_2, 'Apt 101')
        self.assertEqual(updated_profile.city, 'Brisbane')
        self.assertEqual(updated_profile.state, 'QLD')
        self.assertEqual(updated_profile.post_code, '4000')
        self.assertEqual(updated_profile.country, 'AU')
        self.assertEqual(updated_profile.pk, existing_profile.pk) # Ensure it's the same instance


    def test_form_optional_fields(self):
        """
        Test that optional fields (address_line_2, state) can be left blank.
        """
        data = self.valid_service_profile_data.copy()
        data['address_line_2'] = '' # Ensure it's an empty string in the input data
        data['state'] = '' # Ensure it's an empty string in the input data
        form = ServiceBookingUserForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid with empty optional fields: {form.errors}")
        # When blank=True, null=True, Django forms will clean empty strings to None
        self.assertIsNone(form.cleaned_data['address_line_2'])
        self.assertIsNone(form.cleaned_data['state'])

