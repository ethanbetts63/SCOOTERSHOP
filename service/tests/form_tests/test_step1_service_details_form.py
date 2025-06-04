from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, time, timedelta

# Import the form
from service.forms import ServiceDetailsForm # Assuming forms are in service/forms.py

# Import factories for related models
from ..test_helpers.model_factories import ServiceTypeFactory
from service.models import ServiceType # Import the model directly to query

class ServiceDetailsFormTest(TestCase):
    """
    Tests for the ServiceDetailsForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create active and inactive service types for queryset testing.
        """
        cls.active_service_type_1 = ServiceTypeFactory(name="Oil Change", is_active=True)
        cls.active_service_type_2 = ServiceTypeFactory(name="Tire Replacement", is_active=True)
        cls.inactive_service_type = ServiceTypeFactory(name="Engine Rebuild", is_active=False)

        # Define some common valid data for convenience
        cls.valid_data = {
            'service_type': cls.active_service_type_1.pk,
            'dropoff_date': date.today() + timedelta(days=7),
            'dropoff_time': '09:00',
        }
        # Example choices for dropoff_time (would be dynamically populated in view)
        cls.time_choices = [
            ('09:00', '09:00 AM'),
            ('10:00', '10:00 AM'),
            ('11:00', '11:00 AM'),
        ]

    def test_form_valid_data(self):
        """
        Test that the form is valid with all correct data.
        """
        form = ServiceDetailsForm(data=self.valid_data)
        # Manually set choices for dropoff_time as they are dynamic
        form.fields['dropoff_time'].choices = self.time_choices
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['service_type'], self.active_service_type_1)
        self.assertEqual(form.cleaned_data['dropoff_date'], self.valid_data['dropoff_date'])
        self.assertEqual(form.cleaned_data['dropoff_time'], self.valid_data['dropoff_time'])


    def test_form_invalid_data_missing_fields(self):
        """
        Test that the form is invalid if required fields are missing.
        """
        # Test missing service_type
        data = self.valid_data.copy()
        data['service_type'] = ''
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices # Still need to set choices
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('This field is required.', form.errors['service_type'])

        # Test missing dropoff_date
        data = self.valid_data.copy()
        data['dropoff_date'] = ''
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn('This field is required.', form.errors['dropoff_date'])

        # Test missing dropoff_time
        data = self.valid_data.copy()
        data['dropoff_time'] = ''
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices # Choices are set, but input is empty
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_time', form.errors)
        self.assertIn('This field is required.', form.errors['dropoff_time'])

    def test_service_type_queryset(self):
        """
        Test that the service_type queryset only includes active service types.
        """
        form = ServiceDetailsForm()
        # Get the queryset used by the field
        queryset = form.fields['service_type'].queryset

        # Assert that active service types are in the queryset
        self.assertIn(self.active_service_type_1, queryset)
        self.assertIn(self.active_service_type_2, queryset)
        # Assert that the inactive service type is NOT in the queryset
        self.assertNotIn(self.inactive_service_type, queryset)
        # Assert the count matches only active ones
        self.assertEqual(queryset.count(), ServiceType.objects.filter(is_active=True).count())


    def test_dropoff_date_past_date_validation(self):
        """
        Test that dropoff_date cannot be in the past.
        """
        # Test with a past date
        past_date = date.today() - timedelta(days=1)
        data = self.valid_data.copy()
        data['dropoff_date'] = past_date
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices
        
        self.assertFalse(form.is_valid()) # Should be False because of past date
        self.assertIn('dropoff_date', form.errors)
        self.assertIn('Drop-off date cannot be in the past.', form.errors['dropoff_date'])

        # Test with today's date (should be valid)
        today_date = date.today()
        data = self.valid_data.copy()
        data['dropoff_date'] = today_date
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices
        self.assertTrue(form.is_valid(), f"Form is not valid with today's date: {form.errors}")
        self.assertEqual(form.cleaned_data['dropoff_date'], today_date)

        # Test with a future date (should be valid)
        future_date = date.today() + timedelta(days=1)
        data = self.valid_data.copy()
        data['dropoff_date'] = future_date
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices
        self.assertTrue(form.is_valid(), f"Form is not valid with future date: {form.errors}")
        self.assertEqual(form.cleaned_data['dropoff_date'], future_date)

    def test_dropoff_time_choices_validation(self):
        """
        Test that dropoff_time validates against the provided choices.
        """
        # Test with a valid time choice
        data = self.valid_data.copy()
        data['dropoff_time'] = '10:00'
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices
        self.assertTrue(form.is_valid(), f"Form is not valid with valid time: {form.errors}")
        self.assertEqual(form.cleaned_data['dropoff_time'], '10:00')

        # Test with an invalid time choice
        data = self.valid_data.copy()
        data['dropoff_time'] = '08:30' # Not in self.time_choices
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = self.time_choices
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_time', form.errors)
        self.assertIn('Select a valid choice. 08:30 is not one of the available choices.', form.errors['dropoff_time'])

        # Test with empty choices (should fail if a value is provided)
        data = self.valid_data.copy()
        data['dropoff_time'] = '09:00'
        form = ServiceDetailsForm(data=data)
        form.fields['dropoff_time'].choices = [] # No choices provided
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_time', form.errors)
        self.assertIn('Select a valid choice. 09:00 is not one of the available choices.', form.errors['dropoff_time'])

