import factory
import datetime
from django.contrib.auth import get_user_model
from mailer.models.EmailLog_model import EmailLog
from service.models import ServiceProfile, ServiceBooking, ServiceType, CustomerMotorcycle
from inventory.models import SalesProfile, SalesBooking, Motorcycle
from decimal import Decimal
from faker import Faker
from payments.models import Payment
import uuid

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


class ServiceTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceType

    name = factory.Sequence(lambda n: f"Service Type {n}")
    description = factory.Faker("paragraph")
    estimated_duration = factory.Faker("random_int", min=1, max=30)
    base_price = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    is_active = True
    image = None


class ServiceProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")
    email = factory.LazyAttribute(
        lambda o: o.user.email if o.user else factory.Faker("email")
    )
    phone_number = factory.LazyFunction(lambda: fake.numerify("##########"))
    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")
    post_code = factory.Faker("postcode")
    country = factory.Faker("country_code")


class CustomerMotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerMotorcycle

    service_profile = factory.SubFactory(ServiceProfileFactory)
    brand = factory.Faker(
        "word",
        ext_word_list=[
            "Honda",
            "Yamaha",
            "Kawasaki",
            "Suzuki",
            "Ducati",
            "Harley-Davidson",
            "Other",
        ],
    )
    model = factory.Faker("word")
    year = factory.LazyFunction(lambda: fake.year())
    engine_size = factory.Faker("numerify", text="###cc")
    rego = factory.Faker("bothify", text="???###")
    vin_number = factory.Faker("bothify", text="#################")
    odometer = factory.Faker("random_int", min=0, max=100000)
    transmission = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in CustomerMotorcycle.transmission_choices],
    )
    engine_number = factory.Faker("bothify", text="######")


class ServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBooking

    service_booking_reference = factory.Sequence(lambda n: f"SERVICE-{n:08d}")
    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(
        CustomerMotorcycleFactory,
        service_profile=factory.SelfAttribute("..service_profile"),
    )
    calculated_total = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True)
    )
    calculated_deposit_amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    )
    amount_paid = factory.LazyAttribute(lambda o: o.calculated_total)
    payment_status = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in ServiceBooking.PAYMENT_STATUS_CHOICES],
    )
    payment_method = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in ServiceBooking.PAYMENT_METHOD_CHOICES],
    )
    currency = "AUD"
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    dropoff_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+30d")
    )
    dropoff_time = factory.Faker("time_object")

    service_date = factory.LazyAttribute(
        lambda o: o.dropoff_date
        + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )

    estimated_pickup_date = factory.LazyAttribute(
        lambda o: o.service_date
        + datetime.timedelta(days=fake.random_int(min=1, max=5))
    )

    booking_status = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in ServiceBooking.BOOKING_STATUS_CHOICES],
    )
    customer_notes = factory.Faker("paragraph")


class SalesProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")
    email = factory.LazyAttribute(
        lambda o: o.user.email if o.user else factory.Faker("email")
    )
    phone_number = factory.Faker("phone_number")

    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")
    post_code = factory.Faker("postcode")
    country = factory.Faker("country_code")

    drivers_license_image = None
    drivers_license_number = factory.Faker("bothify", text="?#########")
    drivers_license_expiry = factory.LazyFunction(
        lambda: fake.date_between(start_date="+1y", end_date="+5y")
    )

    date_of_birth = factory.Faker("date_of_birth", minimum_age=18, maximum_age=65)


class MotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Motorcycle

    title = factory.LazyAttribute(lambda o: f"{o.year} {o.brand} {o.model}")
    brand = factory.Faker("company")
    model = factory.LazyAttribute(lambda o: fake.word().capitalize())
    year = factory.Faker("year")
    price = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=5, right_digits=2, positive=True)
    )

    vin_number = factory.Sequence(lambda n: f"VIN{uuid.uuid4().hex[:14].upper()}{n}")
    engine_number = factory.Sequence(lambda n: f"ENG{uuid.uuid4().hex[:14].upper()}{n}")

    condition = factory.Faker(
        "random_element",
        elements=factory.LazyFunction(
            lambda: [choice[0] for choice in Motorcycle.CONDITION_CHOICES]
        ),
    )

    odometer = factory.Faker("random_int", min=100, max=100000)
    engine_size = factory.Faker("random_int", min=125, max=1800)
    seats = factory.Faker("random_element", elements=[1, 2, None])
    transmission = factory.Faker(
        "random_element",
        elements=factory.LazyFunction(
            lambda: [choice[0] for choice in Motorcycle.TRANSMISSION_CHOICES]
        ),
    )
    description = factory.Faker("paragraph")
    image = None
    is_available = factory.Faker("boolean")
    rego = factory.Faker("bothify", text="???###")
    rego_exp = factory.LazyFunction(
        lambda: fake.date_between(start_date="+6m", end_date="+5y")
    )
    stock_number = factory.Sequence(lambda n: f"STK-{n:05d}")


class SalesBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)

    sales_booking_reference = factory.Sequence(
        lambda n: f"SBK-{uuid.uuid4().hex[:8].upper()}"
    )
    amount_paid = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    payment_status = "paid"
    currency = "AUD"
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+60d")
    )
    appointment_time = factory.Faker("time_object")

    booking_status = "confirmed"
    customer_notes = factory.Faker("paragraph")


class EmailLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailLog

    timestamp = factory.Faker('date_time_this_year', tzinfo=datetime.timezone.utc)
    sender = factory.Faker('email')
    recipient = factory.Faker('email')
    subject = factory.Faker('sentence')
    status = factory.Faker('random_element', elements=['SENT', 'FAILED', 'PENDING'])
    error_message = None
    user = factory.SubFactory(UserFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    service_booking = factory.SubFactory(ServiceBookingFactory)
    sales_booking = factory.SubFactory(SalesBookingFactory)

class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    amount = Decimal("100.00")
    stripe_payment_method_id = "pm_card_visa"
    stripe_payment_intent_id = factory.LazyFunction(lambda: f"pi_{uuid.uuid4().hex}")
    status = "succeeded"
