import factory
import uuid
from faker import Faker
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from refunds.models import RefundSettings
from inventory.models.sales_booking import SalesBooking
from inventory.models.motorcycle import Motorcycle
from inventory.models.sales_profile import SalesProfile
from service.models.service_booking import ServiceBooking
from service.models.service_type import ServiceType
from service.models.service_profile import ServiceProfile
from service.models.customer_motorcycle import CustomerMotorcycle
from payments.models import Payment

fake = Faker()

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

    phone_number = factory.Faker("phone_number")
    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")
    post_code = factory.Faker("postcode")
    country = factory.Faker("country_code")


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


class MotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Motorcycle

    brand = "Test Brand"
    model = "Test Model"
    year = 2023
    price = Decimal("10000.00")
    engine_size = 125


class SalesProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")
    email = factory.Faker("email")
    phone_number = factory.Faker("phone_number")


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    amount = Decimal("100.00")
    stripe_payment_method_id = "pm_card_visa"
    stripe_payment_intent_id = factory.LazyFunction(lambda: f"pi_{uuid.uuid4().hex}")
    status = "succeeded"


class SalesBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory)
    amount_paid = Decimal("100.00")
    created_at = factory.LazyFunction(timezone.now)


class ServiceTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceType

    name = "Test Service"
    price = Decimal("200.00")


class ServiceProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")
    email = factory.Faker("email")
    phone_number = factory.Faker("phone_number")


class CustomerMotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerMotorcycle

    user = factory.SubFactory(UserFactory)
    brand = "Test Brand"
    model = "Test Model"
    year = 2020


class ServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBooking

    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory)
    payment = factory.SubFactory(PaymentFactory)
    dropoff_date = factory.LazyFunction(timezone.now)
    dropoff_time = "10:00"
    amount_paid = Decimal("100.00")
    payment_method = "online_deposit"