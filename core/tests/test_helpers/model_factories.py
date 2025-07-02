import factory
from faker import Faker
from django.contrib.auth import get_user_model

fake = Faker()

from core.models.enquiry import Enquiry


class EnquiryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enquiry

    name = factory.Faker("name")
    email = factory.Faker("email")
    phone_number = factory.LazyFunction(lambda: fake.numerify("##########"))
    message = factory.Faker("paragraph")


User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False

    phone_number = factory.Faker("phone_number")
    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")
    post_code = factory.Faker("postcode")
    country = factory.Faker("country_code")
