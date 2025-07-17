from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from datetime import datetime
import time

from service.models import ServiceBrand


from inventory.forms.admin_motorcycle_form import MotorcycleForm
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, TempSalesBookingFactory, SalesProfileFactory, MotorcycleConditionFactory, MotorcycleFactory, MotorcycleImageFactory, FeaturedMotorcycleFactory, InventorySettingsFactory, BlockedSalesDateFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory

class ServiceBrandModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_brand = ServiceBrandFactory()

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

    def test_last_updated_field(self):

        service_brand = self.service_brand
        self.assertIsInstance(service_brand.last_updated, datetime)

        old_last_updated = service_brand.last_updated
        service_brand.name = "Updated Name"
        service_brand.save()
        self.assertNotEqual(service_brand.last_updated, old_last_updated)

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
