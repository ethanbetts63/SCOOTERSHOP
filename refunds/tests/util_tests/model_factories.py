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
    cost = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)

class ServiceProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")

class CustomerMotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerMotorcycle

    owner = factory.SubFactory(ServiceProfileFactory)
    make = factory.Faker("word")
    model = factory.Faker("word")
    year = factory.Faker("year")

class ServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBooking

    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory)
    amount_paid = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    payment_method = "online_deposit"
    dropoff_date = factory.LazyFunction(lambda: timezone.now().date() + timezone.timedelta(days=10))
    dropoff_time = factory.LazyFunction(lambda: timezone.now().time())
