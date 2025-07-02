from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from datetime import datetime


from service.models import ServiceBrand


from ..test_helpers.model_factories import ServiceBrandFactory


class ServiceBrandModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_brand = ServiceBrandFactory(image=None)

    def test_service_brand_creation(self):

        self.assertIsInstance(self.service_brand, ServiceBrand)
        self.assertIsNotNone(self.service_brand.pk)

    def test_name_field(self):

        service_brand = self.service_brand
        self.assertEqual(service_brand._meta.get_field("name").max_length, 100)
        self.assertTrue(service_brand._meta.get_field("name").unique)
        self.assertIsInstance(service_brand.name, str)
        self.assertIsNotNone(service_brand.name)
        self.assertEqual(
            service_brand._meta.get_field("name").help_text,
            "Name of the service brand (e.g., 'Yamaha', 'Vespa').",
        )

    def test_image_field(self):

        service_brand = self.service_brand
        image_field = service_brand._meta.get_field("image")
        self.assertTrue(image_field.null)
        self.assertTrue(image_field.blank)
        self.assertEqual(image_field.upload_to, "brands/")

        self.assertEqual(image_field.help_text, "Optional image for this brand.")

        dummy_image = SimpleUploadedFile(
            "test_image.jpg", b"dummy_content", content_type="image/jpeg"
        )
        brand_with_image = ServiceBrandFactory(
            name="Brand with Image", image=dummy_image
        )
        self.assertIsNotNone(brand_with_image.image)
        self.assertIn("brands/", brand_with_image.image.name)

        brand_with_image.image = None
        brand_with_image.save()
        self.assertIsNone(
            brand_with_image.image.name if brand_with_image.image else None
        )

    def test_last_updated_field(self):

        service_brand = self.service_brand
        self.assertIsInstance(service_brand.last_updated, datetime)

        old_last_updated = service_brand.last_updated
        service_brand.name = "Updated Name"
        service_brand.save()
        self.assertGreater(service_brand.last_updated, old_last_updated)

    def test_str_method(self):

        service_brand = self.service_brand
        self.assertEqual(str(service_brand), service_brand.name)

    def test_verbose_name_plural(self):

        self.assertEqual(str(ServiceBrand._meta.verbose_name_plural), "Service Brands")

    def test_unique_name_constraint(self):

        initial_brand = ServiceBrandFactory()
        existing_name = initial_brand.name

        with self.assertRaises(IntegrityError):

            ServiceBrand.objects.create(name=existing_name)
