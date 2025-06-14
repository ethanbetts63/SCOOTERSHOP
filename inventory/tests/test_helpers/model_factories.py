import factory
import datetime
import uuid
from django.contrib.auth import get_user_model
from decimal import Decimal
from faker import Faker

fake = Faker()

# Import models from inventory app
from inventory.models import (
    BlockedSalesDate,
    InventorySettings,
    Motorcycle,
    MotorcycleCondition,
    MotorcycleImage,
    SalesBooking,
    SalesProfile,
    TempSalesBooking,
)

from payments.models import RefundPolicySettings

# Import PAYMENT_STATUS_CHOICES and BOOKING_STATUS_CHOICES directly from the model files
from inventory.models.temp_sales_booking import PAYMENT_STATUS_CHOICES as TEMP_PAYMENT_STATUS_CHOICES
from inventory.models.temp_sales_booking import BOOKING_STATUS_CHOICES as TEMP_BOOKING_STATUS_CHOICES # Added this import
from inventory.models.sales_booking import PAYMENT_STATUS_CHOICES as SALES_PAYMENT_STATUS_CHOICES
from inventory.models.sales_booking import BOOKING_STATUS_CHOICES as SALES_BOOKING_STATUS_CHOICES


# Import Payment model from payments app
# This assumes that the 'payments' app is installed in your Django project
# and payments.models.Payment is correctly defined.
from payments.models import Payment

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.Sequence(lambda n: f'user_{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False

    phone_number = factory.Faker('phone_number')
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True))
    currency = 'AUD'
    status = factory.Faker('random_element', elements=['succeeded', 'requires_action', 'requires_payment_method'])
    description = factory.Faker('sentence')
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")
    stripe_payment_method_id = factory.Sequence(lambda n: f"pm_{uuid.uuid4().hex[:24]}")
    refunded_amount = Decimal('0.00')
    refund_policy_snapshot = {}
    temp_hire_booking = None
    hire_booking = None
    driver_profile = None
    temp_service_booking = None
    service_booking = None
    service_customer_profile = None


class MotorcycleConditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MotorcycleCondition
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'condition_{n}')
    display_name = factory.LazyAttribute(lambda o: fake.word().title())


class MotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Motorcycle

    title = factory.LazyAttribute(lambda o: f"{o.year} {o.brand} {o.model}")
    brand = factory.Faker('word', ext_word_list=['Honda', 'Yamaha', 'Kawasaki', 'Suzuki', 'Ducati', 'Harley-Davidson'])
    model = factory.LazyAttribute(lambda o: fake.word().title())
    year = factory.Faker('year')
    price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=5, right_digits=2, positive=True, min_value=5000))
    
    vin_number = factory.Faker('bothify', text='#################')
    engine_number = factory.Faker('bothify', text='######')
    condition = '' # This is for a single choice field, not the ManyToManyField 'conditions'
    
    odometer = factory.Faker('random_int', min=0, max=100000)
    engine_size = factory.Faker('random_int', min=50, max=1800)
    seats = factory.Faker('random_int', min=1, max=2)
    transmission = factory.Faker('random_element', elements=[choice[0] for choice in Motorcycle.TRANSMISSION_CHOICES])
    description = factory.Faker('paragraph', nb_sentences=5)
    image = None
    is_available = True
    rego = factory.Faker('bothify', text='???###')
    rego_exp = factory.LazyFunction(lambda: fake.date_between(start_date='+6m', end_date='+2y'))
    stock_number = factory.Sequence(lambda n: f"STK-{n:05d}")

    daily_hire_rate = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True, min_value=50, max_value=300))
    hourly_hire_rate = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True, min_value=10, max_value=50))

    # Add the new 'status' field
    status = factory.Faker('random_element', elements=[choice[0] for choice in Motorcycle.STATUS_CHOICES])

    @factory.post_generation
    def conditions(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted is not None:  # Check if 'conditions' was explicitly passed (even if empty list)
            if extracted: # If it's a non-empty list
                for condition_name in extracted:
                    condition, _ = MotorcycleCondition.objects.get_or_create(
                        name=condition_name,
                        defaults={'display_name': condition_name.replace('_', ' ').title()}
                    )
                    obj.conditions.add(condition)
            # If extracted is an empty list [], do nothing (no default condition added)
        else:
            # If 'conditions' was not passed at all, add a default 'used' condition
            condition, _ = MotorcycleCondition.objects.get_or_create(
                name='used',
                defaults={'display_name': 'Used'}
            )
            obj.conditions.add(condition)


class MotorcycleImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MotorcycleImage

    motorcycle = factory.SubFactory(MotorcycleFactory)
    image = factory.django.ImageField(filename='test_motorcycle_image.jpg')


class InventorySettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InventorySettings
        django_get_or_create = ('pk',)

    enable_sales_system = True
    enable_depositless_enquiry = True
    enable_reservation_by_deposit = True
    deposit_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True, min_value=50, max_value=500))
    deposit_lifespan_days = 5
    auto_refund_expired_deposits = True
    enable_sales_new_bikes = True
    enable_sales_used_bikes = True
    require_drivers_license = False
    require_address_info = False
    sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat"
    sales_appointment_start_time = datetime.time(9, 0)
    sales_appointment_end_time = datetime.time(17, 0)
    sales_appointment_spacing_mins = 30
    max_advance_booking_days = 90
    min_advance_booking_hours = 24
    currency_code = 'AUD'
    currency_symbol = '$'
    terms_and_conditions_text = factory.Faker('paragraph', nb_sentences=3)
    enable_viewing_for_enquiry = True # Added this field

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj


class SalesProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesProfile

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

    drivers_license_image = None
    drivers_license_number = factory.Faker('bothify', text='?#########')
    drivers_license_expiry = factory.LazyFunction(lambda: fake.date_between(start_date='+1y', end_date='+5y'))
    
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=65)


class TempSalesBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TempSalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory)

    amount_paid = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    payment_status = factory.Faker('random_element', elements=[choice[0] for choice in TEMP_PAYMENT_STATUS_CHOICES])
    currency = 'AUD'
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    appointment_time = factory.Faker('time_object')
    
    customer_notes = factory.Faker('paragraph')
    # Added new fields as per the request
    booking_status = factory.Faker('random_element', elements=[choice[0] for choice in TEMP_BOOKING_STATUS_CHOICES])
    deposit_required_for_flow = factory.Faker('boolean') # This is correctly on TempSalesBooking
    request_viewing = factory.Faker('boolean')


class SalesBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory)

    sales_booking_reference = factory.Sequence(lambda n: f"SBK-{uuid.uuid4().hex[:8].upper()}")
    amount_paid = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    payment_status = factory.Faker('random_element', elements=[choice[0] for choice in SALES_PAYMENT_STATUS_CHOICES])
    currency = 'AUD'
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+60d'))
    appointment_time = factory.Faker('time_object')

    booking_status = factory.Faker('random_element', elements=[choice[0] for choice in SALES_BOOKING_STATUS_CHOICES])
    customer_notes = factory.Faker('paragraph')


class BlockedSalesDateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockedSalesDate

    start_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    end_date = factory.LazyAttribute(lambda o: o.start_date + datetime.timedelta(days=fake.random_int(min=0, max=7)))
    description = factory.Faker('sentence')

class RefundPolicySettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundPolicySettings

    cancellation_full_payment_full_refund_days = factory.Faker('random_int', min=5, max=10)
    cancellation_full_payment_partial_refund_days = factory.Faker('random_int', min=2, max=4)
    cancellation_full_payment_partial_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([25.00, 50.00, 75.00])))
    cancellation_full_payment_minimal_refund_days = factory.Faker('random_int', min=0, max=1)
    cancellation_full_payment_minimal_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([0.00, 10.00, 20.00])))

    cancellation_deposit_full_refund_days = factory.Faker('random_int', min=5, max=10)
    cancellation_deposit_partial_refund_days = factory.Faker('random_int', min=2, max=4)
    cancellation_deposit_partial_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([25.00, 50.00, 75.00])))
    cancellation_deposit_minimal_refund_days = factory.Faker('random_int', min=0, max=1)
    cancellation_deposit_minimal_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([0.00, 10.00, 20.00])))

    refund_deducts_stripe_fee_policy = factory.Faker('boolean')
    stripe_fee_percentage_domestic = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.0170', '0.0180'])))
    stripe_fee_fixed_domestic = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.30', '0.40'])))
    stripe_fee_percentage_international = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.0350', '0.0390'])))
    stripe_fee_fixed_international = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.30', '0.40'])))

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj

