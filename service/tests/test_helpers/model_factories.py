import factory
import datetime
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from faker import Faker # <--- Already there

# Initialize Faker outside the factory classes for efficiency
fake = Faker() # <--- Already there

# Import your models from the 'service' app
# Make sure the paths are correct based on your project structure
from service.models import (
    BlockedServiceDate,
    CustomerMotorcycle,
    ServiceBooking,
    ServiceProfile,
    ServiceSettings,
    ServiceType,
    TempServiceBooking,
)

# Import Payment model from the payments app
# Assuming your Payment model is in 'payments.models'
from payments.models import Payment

# Get the User model dynamically
User = get_user_model()

# --- Base Factories ---

class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for Django's custom User model (SCOOTER_SHOP/users/models.py).
    Includes custom fields defined in your User model.
    """
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.Sequence(lambda n: f'user_{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False

    # Custom fields from your User model
    phone_number = factory.Faker('phone_number')
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')
    # id_image and international_id_image are FileFields,
    # typically handled by creating dummy files in tests or leaving blank.
    # We'll leave them blank by default here.

class PaymentFactory(factory.django.DjangoModelFactory):
    """
    Factory for the Payment model from payments/models.py.
    Note: 'hire.TempHireBooking', 'hire.HireBooking', and 'hire.DriverProfile'
    are referenced by string. If you need to create these related objects
    within the PaymentFactory, you'll need to define their factories
    and import them, or pass existing instances.
    For simplicity, we'll make them optional here.
    """
    class Meta:
        model = Payment

    # id is a UUIDField with default=uuid.uuid4, so factory_boy handles it automatically.

    # Foreign Keys - set to None by default, can be overridden or SubFactory-linked
    # You'll need to import and use the actual factories for these if you want them
    # to be automatically created. E.g., temp_hire_booking = factory.SubFactory(TempHireBookingFactory)
    temp_hire_booking = None
    hire_booking = None
    driver_profile = None

    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}_{n}")
    stripe_payment_method_id = factory.Faker('md5') # Just a dummy hash for method ID
    amount = factory.LazyFunction(lambda: Decimal(f"{factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)}"))
    currency = 'AUD'
    status = factory.Faker('random_element', elements=['succeeded', 'requires_payment_method', 'requires_action', 'canceled'])
    description = factory.Faker('sentence')
    metadata = factory.LazyFunction(lambda: {'test_key': factory.Faker('word')})
    refund_policy_snapshot = factory.LazyFunction(lambda: {'policy_version': '1.0', 'deduct_fees': True})
    refunded_amount = factory.LazyFunction(lambda: Decimal(f"{factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)}"))

# --- Service App Model Factories ---

class ServiceTypeFactory(factory.django.DjangoModelFactory):
    """
    Factory for the ServiceType model.
    """
    class Meta:
        model = ServiceType

    name = factory.Sequence(lambda n: f'Service Type {n}')
    description = factory.Faker('paragraph')
    estimated_duration = factory.LazyFunction(
        lambda: datetime.timedelta(hours=fake.random_int(min=1, max=8))
    )
    # Corrected: Directly use fake.pydecimal to get the Decimal value
    base_price = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    is_active = True
    # image field is optional, so we don't need to generate it by default

class ServiceProfileFactory(factory.django.DjangoModelFactory):
    """
    Factory for the ServiceProfile model.
    Links to a User instance.
    """
    class Meta:
        model = ServiceProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker('name')
    email = factory.LazyAttribute(lambda o: o.user.email if o.user else factory.Faker('email'))
    phone_number = factory.Faker('phone_number')
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')

class CustomerMotorcycleFactory(factory.django.DjangoModelFactory):
    """
    Factory for the CustomerMotorcycle model.
    Links to a ServiceProfile instance.
    """
    class Meta:
        model = CustomerMotorcycle

    service_profile = factory.SubFactory(ServiceProfileFactory)
    brand = factory.Faker('word', ext_word_list=['Honda', 'Yamaha', 'Kawasaki', 'Suzuki', 'Ducati', 'Harley-Davidson', 'Other'])
    make = factory.Faker('word')
    model = factory.Faker('word')
    year = factory.LazyFunction(lambda: factory.Faker('year'))
    engine_size = factory.Faker('numerify', text='###cc')
    rego = factory.Faker('bothify', text='???###')
    vin_number = factory.Faker('bothify', text='#################') # 17 characters
    odometer = factory.Faker('random_int', min=0, max=100000)
    transmission = factory.Faker('random_element', elements=[choice[0] for choice in CustomerMotorcycle.transmission_choices])
    engine_number = factory.Faker('bothify', text='######')
    # image field is optional

class BlockedServiceDateFactory(factory.django.DjangoModelFactory):
    """
    Factory for the BlockedServiceDate model.
    """
    class Meta:
        model = BlockedServiceDate

    start_date = factory.LazyFunction(lambda: factory.Faker('date_between', start_date='today', end_date='+30d'))
    end_date = factory.LazyAttribute(lambda o: o.start_date + datetime.timedelta(days=factory.Faker('random_int', min=0, max=7)))
    description = factory.Faker('sentence')

class ServiceSettingsFactory(factory.django.DjangoModelFactory):
    """
    Factory for the ServiceSettings model.
    Enforces the singleton pattern by ensuring only one instance exists.
    """
    class Meta:
        model = ServiceSettings
        # Prevent multiple instances from being created in tests
        # This factory will always retrieve or create the single instance
        django_get_or_create = ('pk',) # Use pk to ensure it's always the same instance

    # Default values for ServiceSettings
    enable_service_booking = True
    booking_advance_notice = 1
    max_visible_slots_per_day = 6
    allow_anonymous_bookings = True
    allow_account_bookings = True
    booking_open_days = "Mon,Tue,Wed,Thu,Fri"
    enable_service_brands = True
    other_brand_policy_text = factory.Faker('paragraph')
    enable_deposit = False
    deposit_calc_method = 'FLAT_FEE'
    deposit_flat_fee_amount = Decimal('0.00')
    deposit_percentage = Decimal('0.00')
    enable_online_full_payment = False
    enable_online_deposit = True
    enable_instore_full_payment = True
    currency_code = 'AUD'
    currency_symbol = '$'
    cancel_full_payment_max_refund_days = 7
    cancel_full_payment_max_refund_percentage = Decimal('1.00')
    cancel_full_payment_partial_refund_days = 3
    cancel_full_payment_partial_refund_percentage = Decimal('0.50')
    cancel_full_payment_min_refund_days = 1
    cancel_full_payment_min_refund_percentage = Decimal('0.00')
    cancel_deposit_max_refund_days = 7
    cancel_deposit_max_refund_percentage = Decimal('1.00')
    cancel_deposit_partial_refund_days = 3
    cancel_deposit_partial_refund_percentage = Decimal('0.50')
    cancel_deposit_min_refund_days = 1
    cancel_deposit_min_refund_percentage = Decimal('0.00')
    refund_deducts_stripe_fee_policy = True
    stripe_fee_percentage = Decimal('0.0290')
    stripe_fee_fixed = Decimal('0.30')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Ensures only one instance of ServiceSettings is created.
        """
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            # If instance already exists, update its fields with kwargs
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj


class TempServiceBookingFactory(factory.django.DjangoModelFactory):
    """
    Factory for the TempServiceBooking model.
    Links to ServiceProfile, ServiceType, and CustomerMotorcycle.
    """
    class Meta:
        model = TempServiceBooking

    session_uuid = factory.LazyFunction(uuid.uuid4)
    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory, service_profile=factory.SelfAttribute('..service_profile'))
    payment_option = factory.Faker('random_element', elements=[choice[0] for choice in TempServiceBooking.PAYMENT_METHOD_CHOICES])
    dropoff_date = factory.LazyFunction(lambda: factory.Faker('date_between', start_date='today', end_date='+30d'))
    dropoff_time = factory.Faker('time_object')
    estimated_pickup_date = None # Set to None by default, can be overridden
    customer_notes = factory.Faker('paragraph')
    calculated_deposit_amount = factory.LazyFunction(lambda: Decimal(f"{factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)}"))


class ServiceBookingFactory(factory.django.DjangoModelFactory):
    """
    Factory for the ServiceBooking model.
    Links to ServiceProfile, ServiceType, CustomerMotorcycle, and Payment.
    """
    class Meta:
        model = ServiceBooking

    booking_reference = factory.Sequence(lambda n: f"SERVICE-{n:08d}")
    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory, service_profile=factory.SelfAttribute('..service_profile'))
    payment_option = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.PAYMENT_METHOD_CHOICES])
    payment = factory.SubFactory(PaymentFactory) # Link to a Payment instance
    calculated_total = factory.LazyFunction(lambda: Decimal(f"{factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)}"))
    calculated_deposit_amount = factory.LazyFunction(lambda: Decimal(f"{factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)}"))
    amount_paid = factory.LazyAttribute(lambda o: o.calculated_total) # Assume full payment by default
    payment_status = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.PAYMENT_STATUS_CHOICES])
    payment_method = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.PAYMENT_METHOD_CHOICES])
    currency = 'AUD'
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")
    dropoff_date = factory.LazyFunction(lambda: factory.Faker('date_between', start_date='today', end_date='+30d'))
    dropoff_time = factory.Faker('time_object')
    estimated_pickup_date = factory.LazyAttribute(lambda o: o.dropoff_date + datetime.timedelta(days=factory.Faker('random_int', min=1, max=5)))
    booking_status = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.BOOKING_STATUS_CHOICES])
    customer_notes = factory.Faker('paragraph')
