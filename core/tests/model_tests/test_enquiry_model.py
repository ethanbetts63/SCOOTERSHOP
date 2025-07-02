from django.test import TestCase
from django.db import models
from core.models.enquiry import Enquiry
from ..test_helpers.model_factories import EnquiryFactory

class EnquiryModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.enquiry = EnquiryFactory()

    def test_enquiry_creation(self):
        self.assertIsNotNone(self.enquiry)
        self.assertIsInstance(self.enquiry, Enquiry)
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_str_method(self):
        expected_str = f"Enquiry from {self.enquiry.name} ({self.enquiry.email})"
        self.assertEqual(str(self.enquiry), expected_str)

    def test_field_attributes(self):
        enquiry = self.enquiry

       

        field = enquiry._meta.get_field('name')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 100)

       

        field = enquiry._meta.get_field('email')
        self.assertIsInstance(field, models.EmailField)

       

        field = enquiry._meta.get_field('phone_number')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

       

        field = enquiry._meta.get_field('message')
        self.assertIsInstance(field, models.TextField)

       

        field = enquiry._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)

    def test_verbose_name_plural(self):
        self.assertEqual(Enquiry._meta.verbose_name_plural, "Enquiries")
