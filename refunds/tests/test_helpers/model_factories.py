import factory
from payments.tests.test_helpers.model_factories import PaymentFactory
from refunds.models import RefundRequest, RefundSettings, RefundTerms
from django.utils import timezone
from faker import Faker

fake = Faker()
import uuid


class RefundSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundSettings

    deposit_full_refund_days = 10
    deposit_partial_refund_days = 5
    deposit_no_refund_days = 2
    deposit_partial_refund_percentage = 50

    full_payment_full_refund_days = 10
    full_payment_partial_refund_days = 5
    full_payment_no_refund_percentage = 2
    full_payment_partial_refund_percentage = 60


class RefundRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundRequest

    service_booking = None
    sales_booking = None
    service_profile = None
    sales_profile = None

    payment = factory.SubFactory(PaymentFactory)

    reason = factory.Faker("paragraph")
    rejection_reason = None
    requested_at = factory.LazyFunction(timezone.now)
    status = factory.Faker(
        "random_element",
        elements=[
            "unverified",
            "pending",
            "reviewed_pending_approval",
            "approved",
            "rejected",
            "partially_refunded",
            "refunded",
            "failed",
        ],
    )
    amount_to_refund = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    processed_by = None
    processed_at = None
    stripe_refund_id = factory.Sequence(lambda n: f"re_{uuid.uuid4().hex[:24]}_{n}")
    is_admin_initiated = factory.Faker("boolean")
    refund_calculation_details = factory.LazyFunction(
        lambda: {
            "policy_version": "1.0",
            "refunded_amount": str(
                fake.pydecimal(left_digits=2, right_digits=2, positive=True)
            ),
            "sales_grace_period_applied": fake.boolean(),
            "sales_grace_period_hours": fake.random_int(min=12, max=72),
        }
    )
    request_email = factory.Faker("email")
    verification_token = factory.LazyFunction(uuid.uuid4)
    token_created_at = factory.LazyFunction(timezone.now)


class RefundTermsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundTerms

    content = factory.Faker("paragraph")
    version_number = factory.Sequence(lambda n: n + 1)
    is_active = factory.Faker("boolean")
