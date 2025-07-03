import factory
import datetime
from django.contrib.auth import get_user_model
from mailer.models.EmailLog_model import EmailLog
from service.tests.test_helpers.model_factories import ServiceProfileFactory, ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesProfileFactory, SalesBookingFactory

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("uuid4")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False


class EmailLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailLog

    timestamp = factory.Faker('date_time_this_year', tzinfo=datetime.timezone.utc)
    sender = factory.Faker('email')
    recipient = factory.Faker('email')
    subject = factory.Faker('sentence')
    body = factory.Faker('paragraph')
    status = factory.Faker('random_element', elements=['SENT', 'FAILED', 'PENDING'])
    error_message = None
    user = factory.SubFactory(UserFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    service_booking = factory.SubFactory(ServiceBookingFactory)
    sales_booking = factory.SubFactory(SalesBookingFactory)