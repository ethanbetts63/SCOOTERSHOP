import factory
import datetime
from mailer.models import EmailLog
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceProfileFactory,
)
from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    SalesProfileFactory,
)


class EmailLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailLog

    timestamp = factory.Faker("date_time_this_year", tzinfo=datetime.timezone.utc)
    sender = factory.Faker("email")
    recipient = factory.Faker("email")
    subject = factory.Faker("sentence")
    status = factory.Faker("random_element", elements=["SENT", "FAILED", "PENDING"])
    error_message = None
    user = factory.SubFactory(UserFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    service_booking = factory.SubFactory(ServiceBookingFactory)
    sales_booking = factory.SubFactory(SalesBookingFactory)
