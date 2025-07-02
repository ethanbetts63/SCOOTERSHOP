import factory
from faker import Faker

fake = Faker()

from core.models.enquiry import Enquiry

class EnquiryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enquiry

    name = factory.Faker('name')
    email = factory.Faker('email')
    phone_number = factory.LazyFunction(lambda: fake.numerify('##########'))
    message = factory.Faker('paragraph')
