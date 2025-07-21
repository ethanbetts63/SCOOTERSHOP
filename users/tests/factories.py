import factory
from factory.faker import Faker
from users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = Faker('user_name')
    email = Faker('email')
    password = factory.PostGenerationMethodCall('set_password', 'default_password')
    is_staff = True
    is_superuser = True
