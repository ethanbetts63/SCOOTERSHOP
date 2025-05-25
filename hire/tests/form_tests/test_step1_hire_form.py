# hire/tests/form_tests/test_step1_hire_form.py

from django.test import TestCase
from django.core.exceptions import ValidationError
import datetime

from hire.forms.step1_DateTime_form import Step1DateTimeForm

class Step1DateTimeFormTests(TestCase):
    """
    Tests for the Step1DateTimeForm, focusing on its clean method.
    """

    def test_valid_pickup_and_return_datetimes(self):
        """
        Test that the form is valid when return datetime is after pickup datetime.
        """
        form_data = {
            'pick_up_date': datetime.date(2025, 6, 1),
            'pick_up_time': datetime.time(10, 0),
            'return_date': datetime.date(2025, 6, 2),
            'return_time': datetime.time(10, 0),
            'has_motorcycle_license': True,
        }
        form = Step1DateTimeForm(data=form_data)
        self.assertTrue(form.is_valid())
        # Ensure no validation errors were added to specific fields
        self.assertNotIn('__all__', form.errors)

    def test_return_datetime_before_pickup_datetime(self):
        """
        Test that the form raises a ValidationError when return datetime
        is before pickup datetime.
        """
        form_data = {
            'pick_up_date': datetime.date(2025, 6, 2),
            'pick_up_time': datetime.time(10, 0),
            'return_date': datetime.date(2025, 6, 1),
            'return_time': datetime.time(10, 0),
            'has_motorcycle_license': False,
        }
        form = Step1DateTimeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn("Return date and time must be after pickup date and time.", form.errors['__all__'])

    def test_return_datetime_same_as_pickup_datetime(self):
        """
        Test that the form raises a ValidationError when return datetime
        is the same as pickup datetime.
        """
        form_data = {
            'pick_up_date': datetime.date(2025, 6, 1),
            'pick_up_time': datetime.time(10, 0),
            'return_date': datetime.date(2025, 6, 1),
            'return_time': datetime.time(10, 0),
            'has_motorcycle_license': True,
        }
        form = Step1DateTimeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn("Return date and time must be after pickup date and time.", form.errors['__all__'])

    def test_missing_pickup_date(self):
        """
        Test that the form handles missing pickup_date gracefully (Django's default required validation).
        """
        form_data = {
            'pick_up_time': datetime.time(10, 0),
            'return_date': datetime.date(2025, 6, 2),
            'return_time': datetime.time(10, 0),
            'has_motorcycle_license': False,
        }
        form = Step1DateTimeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('pick_up_date', form.errors) # Django's default 'required' error

    def test_missing_return_time(self):
        """
        Test that the form handles missing return_time gracefully (Django's default required validation).
        """
        form_data = {
            'pick_up_date': datetime.date(2025, 6, 1),
            'pick_up_time': datetime.time(10, 0),
            'return_date': datetime.date(2025, 6, 2),
            'has_motorcycle_license': True,
        }
        form = Step1DateTimeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('return_time', form.errors) # Django's default 'required' error

    def test_only_has_motorcycle_license_provided(self):
        """
        Test that the form is not valid if only has_motorcycle_license is provided.
        """
        form_data = {
            'has_motorcycle_license': True,
        }
        form = Step1DateTimeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('pick_up_date', form.errors)
        self.assertIn('pick_up_time', form.errors)
        self.assertIn('return_date', form.errors)
        self.assertIn('return_time', form.errors)
        self.assertNotIn('__all__', form.errors) # No custom clean error yet as datetime fields are missing
