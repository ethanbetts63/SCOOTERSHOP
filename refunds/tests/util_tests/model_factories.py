import factory
from faker import Faker
from django.utils import timezone
from service.models import ServiceBooking, ServiceType, ServiceProfile, CustomerMotorcycle
from core.tests.test_helpers.model_factories import UserFactory

fake = Faker()

class ServiceTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceType

    name = factory.Faker("word")
    description = factory.Faker("text")
    estimated_duration = factory.Faker("random_int", min=1, max=5)
    base_price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)

class ServiceProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")

class CustomerMotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerMotorcycle

    service_profile = factory.SubFactory(ServiceProfileFactory)
    brand = factory.Faker("word")
    model = factory.Faker("word")
    year = factory.Faker("year")
    rego = factory.Faker("license_plate")
    odometer = factory.Faker("random_int", min=1000, max=50000)
    transmission = "MANUAL"
    engine_size = "250cc"

class ServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBooking

    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory)
    amount_paid = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    payment_method = "online_deposit"
    service_date = factory.LazyFunction(lambda: timezone.now().date() + timezone.timedelta(days=10))
    dropoff_date = factory.LazyFunction(lambda: timezone.now().date() + timezone.timedelta(days=10))
    dropoff_time = factory.LazyFunction(lambda: timezone.now().time())
