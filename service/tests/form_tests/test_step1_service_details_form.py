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
        # 'dropoff_date' and 'dropoff_time' have been removed/renamed from the form
        cls.valid_data = {
            'service_type': cls.active_service_type_1.pk,
            'service_date': date.today() + timedelta(days=7), # Renamed from dropoff_date
        }
        # Removed cls.time_choices as dropoff_time field no longer exists in the form

    def test_form_valid_data(self):
        """
        Test that the form is valid with all correct data.
        """
        form = ServiceDetailsForm(data=self.valid_data)
        # No need to manually set choices for dropoff_time as it's removed
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['service_type'], self.active_service_type_1)
        self.assertEqual(form.cleaned_data['service_date'], self.valid_data['service_date'])
        # Removed assertion for dropoff_time as it's no longer in the form


    def test_form_invalid_data_missing_fields(self):
        """
        Test that the form is invalid if required fields are missing.
        """
        # Test missing service_type
        data = self.valid_data.copy()
        data['service_type'] = ''
        form = ServiceDetailsForm(data=data)
        # No need to set choices for dropoff_time
        self.assertFalse(form.is_valid())
        self.assertIn('service_type', form.errors)
        self.assertIn('This field is required.', form.errors['service_type'])

        # Test missing service_date (updated from dropoff_date)
        data = self.valid_data.copy()
        data['service_date'] = ''
        form = ServiceDetailsForm(data=data)
        # No need to set choices for dropoff_time
        self.assertFalse(form.is_valid())
        self.assertIn('service_date', form.errors)
        self.assertIn('This field is required.', form.errors['service_date'])

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


    def test_service_date_past_date_validation(self): # Renamed from test_dropoff_date_past_date_validation
        """
        Test that service_date cannot be in the past.
        """
        # Test with a past date
        past_date = date.today() - timedelta(days=1)
        data = self.valid_data.copy()
        data['service_date'] = past_date # Updated field name
        form = ServiceDetailsForm(data=data)
        # No need to set choices for dropoff_time
        
        self.assertFalse(form.is_valid()) # Should be False because of past date
        self.assertIn('service_date', form.errors) # Updated field name
        self.assertIn('Service date cannot be in the past.', form.errors['service_date']) # Updated error message

        # Test with today's date (should be valid)
        today_date = date.today()
        data = self.valid_data.copy()
        data['service_date'] = today_date # Updated field name
        form = ServiceDetailsForm(data=data)
        # No need to set choices for dropoff_time
        self.assertTrue(form.is_valid(), f"Form is not valid with today's date: {form.errors}")
        self.assertEqual(form.cleaned_data['service_date'], today_date) # Updated field name

        # Test with a future date (should be valid)
        future_date = date.today() + timedelta(days=1)
        data = self.valid_data.copy()
        data['service_date'] = future_date # Updated field name
        form = ServiceDetailsForm(data=data)
        # No need to set choices for dropoff_time
        self.assertTrue(form.is_valid(), f"Form is not valid with future date: {form.errors}")
        self.assertEqual(form.cleaned_data['service_date'], future_date) # Updated field name

    