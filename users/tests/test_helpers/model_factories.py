import factory
from faker import Faker
from django.contrib.auth import get_user_model

fake = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False


class StaffUserFactory(UserFactory):
    is_staff = True
    password = factory.PostGenerationMethodCall("set_password", "password123")


class SuperUserFactory(UserFactory):
    is_staff = True
    is_superuser = True
    password = factory.PostGenerationMethodCall("set_password", "password123")
