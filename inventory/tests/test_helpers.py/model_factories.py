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

# Import Payment model from payments app
from payments.models import Payment

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for Django's built-in User model.
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

    phone_number = factory.Faker('phone_number')
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')


class PaymentFactory(factory.django.DjangoModelFactory):
    """
    Factory for the Payment model from the payments app.
    Note: This is a placeholder and should align with your actual Payment model fields.
    """
    class Meta:
        model = Payment

    amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True))
    currency = 'AUD'
    status = factory.Faker('random_element', elements=['succeeded', 'requires_action', 'requires_payment_method'])
    description = factory.Faker('sentence')
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")
    stripe_payment_method_id = factory.Sequence(lambda n: f"pm_{uuid.uuid4().hex[:24]}")
    refunded_amount = Decimal('0.00')
    refund_policy_snapshot = {} # Assuming this is a JSONField or similar
    # Null out foreign keys that are not relevant to sales bookings for clarity
    temp_hire_booking = None
    hire_booking = None
    driver_profile = None
    temp_service_booking = None
    service_booking = None
    service_customer_profile = None


class MotorcycleConditionFactory(factory.django.DjangoModelFactory):
    """
    Factory for the MotorcycleCondition model.
    """
    class Meta:
        model = MotorcycleCondition
        django_get_or_create = ('name',) # Ensures unique conditions are created once

    name = factory.Sequence(lambda n: f'condition_{n}')
    display_name = factory.Faker('word').title()


class MotorcycleFactory(factory.django.DjangoModelFactory):
    """
    Factory for the Motorcycle model.
    """
    class Meta:
        model = Motorcycle

    title = factory.LazyAttribute(lambda o: f"{o.year} {o.brand} {o.model}")
    brand = factory.Faker('word', ext_word_list=['Honda', 'Yamaha', 'Kawasaki', 'Suzuki', 'Ducati', 'Harley-Davidson'])
    model = factory.Faker('word').title()
    year = factory.Faker('year')
    price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=5, right_digits=2, positive=True, min_value=5000))
    
    vin_number = factory.Faker('bothify', text='#################')
    engine_number = factory.Faker('bothify', text='######')
    owner = factory.SubFactory(UserFactory) # Link to a User
    
    # We will use the ManyToMany 'conditions' field primarily
    condition = '' # Set to empty string as 'conditions' ManyToMany is preferred
    
    odometer = factory.Faker('random_int', min=0, max=100000)
    engine_size = factory.Faker('random_int', min=50, max=1800)
    seats = factory.Faker('random_int', min=1, max=2)
    transmission = factory.Faker('random_element', elements=[choice[0] for choice in Motorcycle.TRANSMISSION_CHOICES])
    description = factory.Faker('paragraph', nb_sentences=5)
    image = None # FileField, set to None for factory
    is_available = True
    rego = factory.Faker('bothify', text='???###')
    rego_exp = factory.LazyFunction(lambda: fake.date_between(start_date='+6m', end_date='+2y'))
    stock_number = factory.Sequence(lambda n: f"STK-{n:05d}")

    daily_hire_rate = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True, min_value=50, max_value=300))
    hourly_hire_rate = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True, min_value=10, max_value=50))

    @factory.post_generation
    def conditions(obj, create, extracted, **kwargs):
        """
        Adds multiple MotorcycleCondition instances to the motorcycle.
        Can be used like: MotorcycleFactory(conditions=['new', 'used'])
        """
        if not create:
            # Don't add conditions if we're not creating an instance
            return

        if extracted:
            # A list of condition names was passed, e.g., ['new', 'used']
            for condition_name in extracted:
                condition, _ = MotorcycleCondition.objects.get_or_create(
                    name=condition_name,
                    defaults={'display_name': condition_name.replace('_', ' ').title()}
                )
                obj.conditions.add(condition)
        else:
            # If no conditions are specified, add a default 'used' condition
            condition, _ = MotorcycleCondition.objects.get_or_create(
                name='used',
                defaults={'display_name': 'Used'}
            )
            obj.conditions.add(condition)


class MotorcycleImageFactory(factory.django.DjangoModelFactory):
    """
    Factory for the MotorcycleImage model.
    """
    class Meta:
        model = MotorcycleImage

    motorcycle = factory.SubFactory(MotorcycleFactory)
    image = factory.django.ImageField(filename='test_motorcycle_image.jpg') # Creates a dummy image file


class InventorySettingsFactory(factory.django.DjangoModelFactory):
    """
    Factory for the InventorySettings singleton model.
    Ensures that only one instance of InventorySettings can be created or updated.
    """
    class Meta:
        model = InventorySettings
        django_get_or_create = ('pk',) # Enforces singleton pattern by always trying to get pk=1

    enable_sales_system = True
    enable_depositless_enquiry = True
    enable_reservation_by_deposit = True
    deposit_amount = Decimal('100.00')
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

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Custom _create method to enforce the singleton pattern.
        Always creates or updates the single instance with pk=1.
        """
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            # If an instance already exists, update its fields
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj


class SalesProfileFactory(factory.django.DjangoModelFactory):
    """
    Factory for the SalesProfile model.
    """
    class Meta:
        model = SalesProfile

    user = factory.SubFactory(UserFactory) # Optional link to a User
    name = factory.Faker('name')
    email = factory.LazyAttribute(lambda o: o.user.email if o.user else factory.Faker('email'))
    phone_number = factory.Faker('phone_number')
    
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')

    drivers_license_image = None # FileField, set to None
    drivers_license_number = factory.Faker('bothify', text='?#########')
    drivers_license_expiry = factory.LazyFunction(lambda: fake.date_between(start_date='+1y', end_date='+5y'))
    
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=65)


class TempSalesBookingFactory(factory.django.DjangoModelFactory):
    """
    Factory for the TempSalesBooking model, representing an incomplete booking.
    """
    class Meta:
        model = TempSalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory) # Optional payment link

    sales_booking_reference = factory.Sequence(lambda n: f"TSB-{uuid.uuid4().hex[:8].upper()}")
    amount_paid = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    payment_status = factory.Faker('random_element', elements=[choice[0] for choice in TempSalesBooking.PAYMENT_STATUS_CHOICES])
    currency = 'AUD'
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    appointment_time = factory.Faker('time_object')
    
    customer_notes = factory.Faker('paragraph')


class SalesBookingFactory(factory.django.DjangoModelFactory):
    """
    Factory for the SalesBooking model, representing a confirmed sales booking.
    """
    class Meta:
        model = SalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory)

    sales_booking_reference = factory.Sequence(lambda n: f"SBK-{uuid.uuid4().hex[:8].upper()}")
    amount_paid = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    payment_status = factory.Faker('random_element', elements=[choice[0] for choice in SalesBooking.PAYMENT_STATUS_CHOICES])
    currency = 'AUD'
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+60d'))
    appointment_time = factory.Faker('time_object')

    booking_status = factory.Faker('random_element', elements=[choice[0] for choice in SalesBooking.BOOKING_STATUS_CHOICES])
    customer_notes = factory.Faker('paragraph')


class BlockedSalesDateFactory(factory.django.DjangoModelFactory):
    """
    Factory for the BlockedSalesDate model.
    """
    class Meta:
        model = BlockedSalesDate

    start_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    end_date = factory.LazyAttribute(lambda o: o.start_date + datetime.timedelta(days=fake.random_int(min=0, max=7)))
    description = factory.Faker('sentence')

