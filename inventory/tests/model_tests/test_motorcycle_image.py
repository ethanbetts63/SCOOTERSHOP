from django.test import TestCase
from inventory.models import Motorcycle, MotorcycleImage
from django.db import models
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory, MotorcycleConditionFactory, MotorcycleFactory, MotorcycleImageFactory, FeaturedMotorcycleFactory, InventorySettingsFactory, BlockedSalesDateFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory


class MotorcycleImageModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.motorcycle = MotorcycleFactory(
            brand="TestBrand", model="TestModel", year=2020
        )
        cls.motorcycle_image = MotorcycleImageFactory(motorcycle=cls.motorcycle)

    def test_motorcycle_image_creation(self):

        self.assertIsInstance(self.motorcycle_image, MotorcycleImage)
        self.assertIsNotNone(self.motorcycle_image.pk)

        self.assertEqual(self.motorcycle_image.motorcycle, self.motorcycle)

    def test_motorcycle_field(self):

        field = self.motorcycle_image._meta.get_field("motorcycle")
        self.assertIsInstance(
            field, type(MotorcycleImage._meta.get_field("motorcycle"))
        )
        self.assertEqual(field.related_model, Motorcycle)
        self.assertEqual(field._related_name, "images")

    def test_image_field(self):

        field = self.motorcycle_image._meta.get_field("image")
        self.assertIsInstance(field, models.FileField)
        self.assertEqual(field.upload_to, "motorcycles/additional/")

        self.assertTrue(self.motorcycle_image.image)
        self.assertGreater(self.motorcycle_image.image.size, 0)

    def test_str_method(self):

        expected_str = f"Image for {self.motorcycle}"
        self.assertEqual(str(self.motorcycle_image), expected_str)

    def test_verbose_names_meta(self):

        self.assertEqual(MotorcycleImage._meta.verbose_name, "motorcycle image")
        self.assertEqual(MotorcycleImage._meta.verbose_name_plural, "motorcycle images")
