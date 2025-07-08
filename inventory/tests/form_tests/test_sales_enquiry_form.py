from django.test import TestCase
from inventory.forms import SalesEnquiryForm
from inventory.tests.test_helpers.model_factories import MotorcycleFactory

class SalesEnquiryFormTest(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory()

    def test_valid_form_data(self):
        form = SalesEnquiryForm(data={
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone_number': '1234567890',
            'message': 'I am interested in this motorcycle.',
            'motorcycle': self.motorcycle.pk,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        form = SalesEnquiryForm(data={
            'name': '',
            'email': '',
            'phone_number': '',
            'message': '',
            'motorcycle': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('message', form.errors)

    def test_invalid_email(self):
        form = SalesEnquiryForm(data={
            'name': 'John Doe',
            'email': 'invalid-email',
            'phone_number': '1234567890',
            'message': 'I am interested in this motorcycle.',
            'motorcycle': self.motorcycle.pk,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'], ['Enter a valid email address.'])