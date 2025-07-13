import factory
import datetime
import uuid
from django.contrib.auth import get_user_model
from decimal import Decimal
from faker import Faker

fake = Faker()

from service.models import (
    BlockedServiceDate,
    CustomerMotorcycle,
    ServiceBooking,
    ServiceProfile,
    ServiceSettings,
    ServiceType,
    TempServiceBooking,
    ServiceBrand,
    Servicefaq,
    ServiceTerms,
)

from payments.models import Payment
from refunds.models import RefundSettings
from dashboard.models import SiteSettings # Import SiteSettings

from service.utils.calculate_estimated_pickup_date import (
    calculate_estimated_pickup_date,
)


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
    password = factory.PostGenerationMethodCall('set_password', 'password123')

    phone_number = factory.Faker("phone_number")
    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")
    post_code = factory.Faker("postcode")
    country = factory.Faker("country_code")

class StaffUserFactory(UserFactory):
    is_staff = True
    password = factory.PostGenerationMethodCall('set_password', 'password123')


class ServiceBrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBrand
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Brand {n}")


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
    email = factory.Faker("email")
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


class BlockedServiceDateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockedServiceDate

    start_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+30d")
    )
    end_date = factory.LazyAttribute(
        lambda o: o.start_date + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )
    description = factory.Faker("sentence")


class ServiceSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceSettings
        django_get_or_create = ("pk",)

    booking_advance_notice = 1
    max_visible_slots_per_day = 6
    booking_open_days = "Mon,Tue,Wed,Thu,Fri"
    drop_off_start_time = datetime.time(9, 0)
    drop_off_end_time = datetime.time(17, 0)
    drop_off_spacing_mins = 30
    max_advance_dropoff_days = 7
    latest_same_day_dropoff_time = datetime.time(12, 0)

    enable_after_hours_dropoff = False
    after_hours_dropoff_disclaimer = factory.Faker("paragraph", nb_sentences=3)
    enable_online_deposit = True,
    deposit_calc_method = "FLAT_FEE"
    deposit_flat_fee_amount = Decimal("1.00")
    deposit_percentage = Decimal("0.00")
    enable_online_full_payment = False
    enable_online_deposit = True
    enable_instore_full_payment = True
    currency_code = "AUD"
    currency_symbol = "$"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj


class TempServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TempServiceBooking

    session_uuid = factory.LazyFunction(uuid.uuid4)
    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(
        CustomerMotorcycleFactory,
        service_profile=factory.SelfAttribute("..service_profile"),
    )
    dropoff_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+30d")
    )
    dropoff_time = factory.Faker("time_object")

    service_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date="today", end_date="+60d")
    )

    @factory.post_generation
    def calculate_estimated_pickup(obj, create, extracted, **kwargs):
        if create:
            calculate_estimated_pickup_date(obj)

    customer_notes = factory.Faker("paragraph")
    calculated_deposit_amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    )
    calculated_total = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True)
    )
    payment_method = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in TempServiceBooking.PAYMENT_METHOD_CHOICES],
    )


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True)
    )
    currency = "AUD"
    status = factory.Faker(
        "random_element",
        elements=["succeeded", "requires_action", "requires_payment_method"],
    )
    description = factory.Faker("sentence")
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")
    stripe_payment_method_id = factory.Sequence(lambda n: f"pm_{uuid.uuid4().hex[:24]}")
    refunded_amount = Decimal("0.00")
    temp_service_booking = None
    service_booking = None
    service_customer_profile = None


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
    payment = factory.SubFactory(PaymentFactory)
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

    service_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+60d")
    )
    dropoff_date = factory.LazyAttribute(lambda o: o.service_date)
    dropoff_time = factory.Faker("time_object")

    @factory.post_generation
    def calculate_estimated_pickup(obj, create, extracted, **kwargs):
        if create:
            calculate_estimated_pickup_date(obj)

    booking_status = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in ServiceBooking.BOOKING_STATUS_CHOICES],
    )
    customer_notes = factory.Faker("paragraph")


class RefundSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundSettings

    full_payment_full_refund_days = factory.Faker(
        "random_int", min=5, max=10
    )
    full_payment_partial_refund_days = factory.Faker(
        "random_int", min=2, max=4
    )
    full_payment_partial_refund_percentage = factory.LazyFunction(
        lambda: Decimal(fake.random_element([25.00, 50.00, 75.00]))
    )
    full_payment_no_refund_percentage = factory.Faker(
        "random_int", min=0, max=1
    )

    deposit_full_refund_days = factory.Faker("random_int", min=5, max=10)
    deposit_partial_refund_days = factory.Faker("random_int", min=2, max=4)
    deposit_partial_refund_percentage = factory.LazyFunction(
        lambda: Decimal(fake.random_element([25.00, 50.00, 75.00]))
    )
    deposit_no_refund_days = factory.Faker("random_int", min=0, max=1)

class ServicefaqFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Servicefaq

    booking_step = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in Servicefaq.BOOKING_STEP_CHOICES],
    )
    question = factory.Faker("sentence")
    answer = factory.Faker("paragraph")
    is_active = True
    display_order = factory.Sequence(lambda n: n)


class ServiceTermsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceTerms

    content = factory.Faker("paragraph")
    version_number = factory.Sequence(lambda n: n + 1)
    is_active = True


class SiteSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteSettings
        django_get_or_create = ('pk',)

    site_name = factory.Faker('company')
    tagline = factory.Faker('catch_phrase')
    email_address = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
    address_line_1 = factory.Faker('street_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country')
    opening_hours_monday = '9:00 AM - 5:00 PM'
    opening_hours_tuesday = '9:00 AM - 5:00 PM'
    opening_hours_wednesday = '9:00 AM - 5:00 PM'
    opening_hours_thursday = '9:00 AM - 5:00 PM'
    opening_hours_friday = '9:00 AM - 5:00 PM'
    opening_hours_saturday = 'Closed'
    opening_hours_sunday = 'Closed'
    facebook_link = factory.Faker('url')
    instagram_link = factory.Faker('url')
    youtube_link = factory.Faker('url')
    tiktok_link = factory.Faker('url')
    enable_sales_enquiries = True
    enable_service_booking = True
    enable_faq_sales = True
    enable_faq_service = True
    enable_refunds = True
    display_address = True
    display_phone = True
    display_email = True
    display_opening_hours = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj