import factory
from core.models import Enquiry
from faker import Faker

fake = Faker()


class EnquiryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enquiry

    name = factory.Faker("name")
    email = factory.Faker("email")
    phone_number = factory.LazyFunction(lambda: fake.numerify("##########"))
    message = factory.Faker("paragraph")
