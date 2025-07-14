import factory
import uuid
from faker import Faker
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import datetime

from refunds.models import RefundSettings
from inventory.models.sales_booking import SalesBooking
from inventory.models.motorcycle import Motorcycle
from inventory.models.sales_profile import SalesProfile
from service.models import (
    ServiceBooking, 
    ServiceType, 
    ServiceProfile, 
    CustomerMotorcycle, 
    ServiceSettings, 
    ServiceBrand, 
    ServiceTerms
)
from payments.models import Payment
from dashboard.models import SiteSettings

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
    base_price = Decimal("200.00")
    estimated_duration = 1 # Add a default value for estimated_duration


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

    service_profile = factory.SubFactory(ServiceProfileFactory)
    brand = "Test Brand"
    model = "Test Model"
    year = 2020
    rego = "TEST123"
    odometer = 10000
    transmission = "MANUAL"
    engine_size = "250cc"


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
    service_date = factory.LazyFunction(timezone.now)

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
    enable_online_deposit = True
    deposit_calc_method = "FLAT_FEE"
    deposit_flat_fee_amount = Decimal("1.00")
    deposit_percentage = Decimal("0.00")
    enable_online_full_payment = False
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

class ServiceBrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBrand
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Brand {n}")

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

    phone_number = factory.Faker('phone_number')
    email_address = factory.Faker('email')
    storefront_address = factory.Faker('address')
    google_places_place_id = factory.Faker('md5')
    youtube_link = factory.Faker('url')
    instagram_link = factory.Faker('url')
    facebook_link = factory.Faker('url')
    opening_hours_monday = '9:00 AM - 5:00 PM'
    opening_hours_tuesday = '9:00 AM - 5:00 PM'
    opening_hours_wednesday = '9:00 AM - 5:00 PM'
    opening_hours_thursday = '9:00 AM - 5:00 PM'
    opening_hours_friday = '9:00 AM - 5:00 PM'
    opening_hours_saturday = 'Closed'
    opening_hours_sunday = 'Closed'

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj