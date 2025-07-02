from django.test import TestCase
from datetime import timedelta
from decimal import Decimal
from service.models import ServiceType
from ..test_helpers.model_factories import ServiceTypeFactory

class ServiceTypeModelTest(TestCase):
    #--

    @classmethod
    def setUpTestData(cls):
        #--
        cls.service_type = ServiceTypeFactory()

    def test_service_type_creation(self):
        #--
        self.assertIsInstance(self.service_type, ServiceType)
        self.assertIsNotNone(self.service_type.pk)                                              

    def test_name_field(self):
        #--
        service_type = self.service_type
        self.assertEqual(service_type._meta.get_field('name').max_length, 100)
        self.assertIsInstance(service_type.name, str)
        self.assertIsNotNone(service_type.name)

    def test_description_field(self):
        #--
        service_type = self.service_type
        self.assertIsInstance(service_type.description, str)
        self.assertIsNotNone(service_type.description)

    def test_estimated_duration_field(self):
        #--
        service_type = self.service_type
                                                    
        self.assertIsInstance(service_type.estimated_duration, int)
        self.assertIsNotNone(service_type.estimated_duration)
                                                                        
        self.assertEqual(service_type._meta.get_field('estimated_duration').help_text, "Estimated number of days to complete this service")


    def test_base_price_field(self):
        #--
        service_type = self.service_type
        self.assertIsInstance(service_type.base_price, Decimal)
        self.assertIsNotNone(service_type.base_price)
        self.assertEqual(service_type._meta.get_field('base_price').max_digits, 8)
        self.assertEqual(service_type._meta.get_field('base_price').decimal_places, 2)
                                                                                      
        new_service_type = ServiceType.objects.create(
            name="New Service",
            description="A new service description",
                                                    
            estimated_duration=1,
                                             
        )
        self.assertEqual(new_service_type.base_price, Decimal('0.00'))

    def test_is_active_field(self):
        #--
        service_type = self.service_type
        self.assertIsInstance(service_type.is_active, bool)
        self.assertEqual(service_type.is_active, True)                                     
        self.assertEqual(service_type._meta.get_field('is_active').help_text, "Whether this service is currently offered")
                                                                                      
        new_service_type = ServiceType.objects.create(
            name="Another Service",
            description="Another service description",
                                                    
            estimated_duration=2,
            base_price=Decimal('50.00')
                                            
        )
        self.assertEqual(new_service_type.is_active, True)

    def test_str_method(self):
        #--
        service_type = self.service_type
        self.assertEqual(str(service_type), service_type.name)

    def test_verbose_name_plural(self):
        #--
        self.assertEqual(str(ServiceType._meta.verbose_name_plural), 'Service Types')

    def test_unique_name(self):
        #--
        ServiceTypeFactory(name="Unique Service Name")
                                                                             
        try:
            ServiceTypeFactory(name="Unique Service Name")
        except Exception as e:
            self.fail(f"Creating duplicate service name raised an exception: {e}")
