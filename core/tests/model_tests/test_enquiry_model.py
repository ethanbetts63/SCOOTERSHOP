from django.test import TestCase
from django.db import models
from core.models.enquiry import Enquiry
from ..test_helpers.model_factories import EnquiryFactory

class EnquiryModelTest(TestCase):
    """
    Tests for the Enquiry model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.enquiry = EnquiryFactory()

    def test_enquiry_creation(self):
        """
        Test that an Enquiry instance can be created using the factory.
        """
        self.assertIsNotNone(self.enquiry)
        self.assertIsInstance(self.enquiry, Enquiry)
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_str_method(self):
        """
        Test the __str__ method of the Enquiry model.
        """
        expected_str = f"Enquiry from {self.enquiry.name} ({self.enquiry.email})"
        self.assertEqual(str(self.enquiry), expected_str)

    def test_field_attributes(self):
        """
        Test the attributes of various fields in the Enquiry model.
        """
        enquiry = self.enquiry

        # Test name field
        field = enquiry._meta.get_field('name')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 100)

        # Test email field
        field = enquiry._meta.get_field('email')
        self.assertIsInstance(field, models.EmailField)

        # Test phone_number field
        field = enquiry._meta.get_field('phone_number')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # Test message field
        field = enquiry._meta.get_field('message')
        self.assertIsInstance(field, models.TextField)

        # Test created_at field
        field = enquiry._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)

    def test_verbose_name_plural(self):
        """
        Test the verbose_name_plural for the Enquiry model.
        """
        self.assertEqual(Enquiry._meta.verbose_name_plural, "Enquiries")
