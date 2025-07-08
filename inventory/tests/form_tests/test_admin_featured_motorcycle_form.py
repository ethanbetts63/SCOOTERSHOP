
from django.test import TestCase
from inventory.forms import FeaturedMotorcycleForm
from inventory.tests.test_helpers.model_factories import MotorcycleFactory
from inventory.models import FeaturedMotorcycle
from django import forms

class FeaturedMotorcycleFormTest(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory()

    def test_valid_form_data(self):
        form = FeaturedMotorcycleForm(data={
            'motorcycle': self.motorcycle.pk,
            'category': FeaturedMotorcycle.CATEGORY_CHOICES[0][0],
            'order': 1
        })
        self.assertTrue(form.is_valid())

    def test_missing_motorcycle(self):
        form = FeaturedMotorcycleForm(data={
            'category': FeaturedMotorcycle.CATEGORY_CHOICES[0][0],
            'order': 1
        })
        self.assertFalse(form.is_valid())
        self.assertIn('motorcycle', form.errors)
        # The form's clean_motorcycle method is not called if the field is entirely missing
        # Django's default required field error is used instead.
        self.assertEqual(form.errors['motorcycle'], ['This field is required.'])

    def test_form_widgets(self):
        form = FeaturedMotorcycleForm()
        self.assertIsInstance(form.fields['motorcycle'].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields['category'].widget, forms.HiddenInput)
        self.assertEqual(form.fields['order'].widget.attrs['class'], 'form-control w-full p-2 border rounded-md')
