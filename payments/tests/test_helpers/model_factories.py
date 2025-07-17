import factory
import uuid
from django.utils import timezone
from faker import Faker
fake = Faker()
from payments.models import Payment, WebhookEvent

class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    temp_service_booking = None
    service_booking = None
    service_customer_profile = None
    temp_sales_booking = None
    sales_booking = None
    sales_customer_profile = None

    stripe_payment_intent_id = factory.Sequence(
        lambda n: f"pi_{uuid.uuid4().hex[:24]}_{n}"
    )
    stripe_payment_method_id = factory.Faker("md5")
    amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    currency = "AUD"

    status = factory.Faker(
        "random_element",
        elements=[
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "succeeded",
            "canceled",
            "failed",
        ],
    )
    description = factory.Faker("sentence")

    metadata = factory.LazyFunction(dict)

    refunded_amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    )


class WebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    stripe_event_id = factory.Sequence(lambda n: f"evt_{uuid.uuid4().hex[:24]}_{n}")
    event_type = factory.Faker(
        "random_element",
        elements=[
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "charge.refunded",
            "customer.created",
            "checkout.session.completed",
        ],
    )
    received_at = factory.LazyFunction(timezone.now)
    payload = factory.LazyFunction(
        lambda: fake.json(num_rows=1, data_columns={"key": "text", "value": "text"})
    )
