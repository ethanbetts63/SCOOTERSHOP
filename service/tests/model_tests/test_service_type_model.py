from django.test import TestCase
from datetime import timedelta
from decimal import Decimal
from service.models import ServiceType
from ..test_helpers.model_factories import ServiceTypeFactory

class ServiceTypeModelTest(TestCase):
    """
    Tests for the ServiceType model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create a single ServiceType instance using the factory.
        """
        cls.service_type = ServiceTypeFactory()

    def test_service_type_creation(self):
        """
        Test that a ServiceType instance can be created successfully using the factory.
        """
        self.assertIsInstance(self.service_type, ServiceType)
        self.assertIsNotNone(self.service_type.pk) # Check if it has a primary key (saved to DB)

    def test_name_field(self):
        """
        Test the 'name' field properties.
        """
        service_type = self.service_type
        self.assertEqual(service_type._meta.get_field('name').max_length, 100)
        self.assertIsInstance(service_type.name, str)
        self.assertIsNotNone(service_type.name)

    def test_description_field(self):
        """
        Test the 'description' field properties.
        """
        service_type = self.service_type
        self.assertIsInstance(service_type.description, str)
        self.assertIsNotNone(service_type.description)

    def test_estimated_duration_field(self):
        """
        Test the 'estimated_duration' field properties and help text.
        """
        service_type = self.service_type
        self.assertIsInstance(service_type.estimated_duration, timedelta)
        self.assertIsNotNone(service_type.estimated_duration)
        self.assertEqual(service_type._meta.get_field('estimated_duration').help_text, "Estimated time to complete this service")

    def test_base_price_field(self):
        """
        Test the 'base_price' field properties and default value.
        """
        service_type = self.service_type
        self.assertIsInstance(service_type.base_price, Decimal)
        self.assertIsNotNone(service_type.base_price)
        self.assertEqual(service_type._meta.get_field('base_price').max_digits, 8)
        self.assertEqual(service_type._meta.get_field('base_price').decimal_places, 2)
        # Check if a newly created instance (without factory override) has the default
        new_service_type = ServiceType.objects.create(
            name="New Service",
            description="A new service description",
            estimated_duration=timedelta(hours=1),
            # base_price will default to 0.00
        )
        self.assertEqual(new_service_type.base_price, Decimal('0.00'))

    def test_is_active_field(self):
        """
        Test the 'is_active' field properties and default value.
        """
        service_type = self.service_type
        self.assertIsInstance(service_type.is_active, bool)
        self.assertEqual(service_type.is_active, True) # Factory sets it to True by default
        self.assertEqual(service_type._meta.get_field('is_active').help_text, "Whether this service is currently offered")
        # Check if a newly created instance (without factory override) has the default
        new_service_type = ServiceType.objects.create(
            name="Another Service",
            description="Another service description",
            estimated_duration=timedelta(hours=2),
            base_price=Decimal('50.00')
            # is_active will default to True
        )
        self.assertEqual(new_service_type.is_active, True)

    # Removed test_image_field as requested.
    # If you later decide to test image uploads, consider using Django's
    # `TemporaryMediaRootMixin` or a more robust approach for file handling in tests.

    def test_str_method(self):
        """
        Test the __str__ method of the ServiceType model.
        It should return the name of the service type.
        """
        service_type = self.service_type
        self.assertEqual(str(service_type), service_type.name)

    def test_verbose_name_plural(self):
        """
        Test the verbose name plural for the model.
        """
        self.assertEqual(str(ServiceType._meta.verbose_name_plural), 'Service Types')

    def test_unique_name(self):
        """
        Test that service names are not implicitly unique (CharField default).
        If you later add unique=True to the name field, this test would fail.
        """
        ServiceTypeFactory(name="Unique Service Name")
        # Should be able to create another with the same name if unique=False
        try:
            ServiceTypeFactory(name="Unique Service Name")
        except Exception as e:
            self.fail(f"Creating duplicate service name raised an exception: {e}")

