import factory
import datetime
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from faker import Faker
import django.apps 

fake = Faker()

from payments.models import Payment, WebhookEvent, RefundRequest, RefundPolicySettings
from hire.models import TempHireBooking, HireBooking, DriverProfile, BookingAddOn, Package, AddOn, TempBookingAddOn
from service.models import ServiceBooking, ServiceProfile, TempServiceBooking, CustomerMotorcycle, ServiceBrand, ServiceType, BlockedServiceDate, ServiceSettings
from inventory.models import Motorcycle, MotorcycleCondition

# Get Django's User model
User = get_user_model()


# Helper function to get model choices safely - Keeping for other models, but not for the problematic ones
def get_model_choices(app_label, model_name, choices_attribute):
    """Safely retrieves choices from a Django model's attribute."""
    # Ensure Django's app registry is ready
    django.apps.apps.check_apps_ready()
    model = django.apps.apps.get_model(app_label, model_name)
    return [choice[0] for choice in getattr(model, choices_attribute)]


# --- Factories for Requested Models (Ordered by Dependency) ---

class MotorcycleConditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MotorcycleCondition
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f"condition_{n}")
    display_name = factory.LazyAttribute(lambda o: o.name.replace('_', ' ').title())

class MotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Motorcycle

    title = factory.LazyAttribute(lambda o: f"{o.year} {o.brand} {o.model}")
    brand = factory.Faker('company')
    model = factory.LazyAttribute(lambda o: fake.word().capitalize())
    year = factory.Faker('year')
    price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=5, right_digits=2, positive=True))

    vin_number = factory.Sequence(lambda n: f"VIN{uuid.uuid4().hex[:14].upper()}{n}")
    engine_number = factory.Sequence(lambda n: f"ENG{uuid.uuid4().hex[:14].upper()}{n}")
    owner = None

    condition = factory.Faker('random_element', elements=factory.LazyFunction(lambda: [choice[0] for choice in Motorcycle.CONDITION_CHOICES]))

    @factory.post_generation
    def conditions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for condition in extracted:
                self.conditions.add(condition)
        else:
            default_condition_name = fake.random_element(elements=['used', 'hire'])
            condition_obj, _ = MotorcycleCondition.objects.get_or_create(
                name=default_condition_name,
                defaults={'display_name': default_condition_name.replace('_', ' ').title()}
            )
            self.conditions.add(condition_obj)

    odometer = factory.Faker('random_int', min=100, max=100000)
    engine_size = factory.Faker('random_int', min=125, max=1800)
    seats = factory.Faker('random_element', elements=[1, 2, None])
    transmission = factory.Faker('random_element', elements=factory.LazyFunction(lambda: [choice[0] for choice in Motorcycle.TRANSMISSION_CHOICES]))
    description = factory.Faker('paragraph')
    image = None
    is_available = factory.Faker('boolean')
    rego = factory.Faker('bothify', text='???###')
    rego_exp = factory.LazyFunction(lambda: fake.date_between(start_date='+6m', end_date='+5y'))
    stock_number = factory.Sequence(lambda n: f"STK-{n:05d}")

    daily_hire_rate = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    hourly_hire_rate = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))


class AddOnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AddOn

    name = factory.Faker('word')
    description = factory.Faker('sentence')
    hourly_cost = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    daily_cost = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    min_quantity = 1
    max_quantity = factory.Faker('random_int', min=1, max=5)
    is_available = factory.Faker('boolean')


class PackageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Package

    name = factory.Faker('word')
    description = factory.Faker('paragraph')
    hourly_cost = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    daily_cost = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    is_available = factory.Faker('boolean')

    @factory.post_generation
    def add_ons(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for add_on in extracted:
                self.add_ons.add(add_on)


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    temp_hire_booking = None
    hire_booking = None
    driver_profile = None
    temp_service_booking = None
    service_booking = None
    service_customer_profile = None

    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}_{n}")
    stripe_payment_method_id = factory.Faker('md5')
    amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    currency = 'AUD'
    # Directly specify common Stripe payment intent statuses
    status = factory.Faker('random_element', elements=[
        'requires_payment_method',
        'requires_confirmation',
        'requires_action',
        'processing',
        'succeeded',
        'canceled',
        'failed',
    ])
    description = factory.Faker('sentence')
    # Changed metadata to use factory.LazyFunction(dict) to default to an empty dictionary
    metadata = factory.LazyFunction(dict)
    refund_policy_snapshot = factory.LazyFunction(lambda: {'policy_version': '1.0', 'deduct_fees': True})
    refunded_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))


class WebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    stripe_event_id = factory.Sequence(lambda n: f"evt_{uuid.uuid4().hex[:24]}_{n}")
    event_type = factory.Faker('random_element', elements=[
        'payment_intent.succeeded',
        'payment_intent.payment_failed',
        'charge.refunded',
        'customer.created',
        'checkout.session.completed'
    ])
    received_at = factory.LazyFunction(timezone.now)
    payload = factory.LazyFunction(lambda: fake.json(num_rows=1, data_columns={'key': 'text', 'value': 'text'}))


class DriverProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DriverProfile

    user = None
    phone_number = factory.Faker('phone_number')
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')
    name = factory.Faker('name')
    email = factory.Faker('email')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=70)
    is_australian_resident = factory.Faker('boolean')

    license_number = factory.Faker('bothify', text='??########')
    international_license_issuing_country = factory.Faker('country')
    license_expiry_date = factory.LazyFunction(lambda: fake.date_between(start_date='+1y', end_date='+10y'))
    international_license_expiry_date = factory.LazyFunction(lambda: fake.date_between(start_date='+1y', end_date='+10y'))
    passport_number = factory.Faker('bothify', text='###########')
    passport_photo = None
    passport_expiry_date = factory.LazyFunction(lambda: fake.date_between(start_date='+1y', end_date='+10y'))

    id_image = None
    international_id_image = None
    license_photo = None
    international_license_photo = None


class TempHireBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TempHireBooking

    session_uuid = factory.LazyFunction(uuid.uuid4)
    pickup_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    pickup_time = factory.Faker('time_object')
    return_date = factory.LazyAttribute(lambda o: o.pickup_date + datetime.timedelta(days=fake.random_int(min=1, max=7)))
    return_time = factory.Faker('time_object')
    has_motorcycle_license = factory.Faker('boolean')

    motorcycle = factory.SubFactory(MotorcycleFactory)
    package = factory.SubFactory(PackageFactory)
    driver_profile = factory.SubFactory(DriverProfileFactory)
    is_international_booking = factory.Faker('boolean')
    # Replaced get_model_choices with a hardcoded list for payment_option
    payment_option = factory.Faker('random_element', elements=['credit_card', 'bank_transfer', 'cash', 'stripe'])

    booked_hourly_rate = factory.LazyAttribute(lambda o: getattr(o.motorcycle, 'hourly_hire_rate', fake.pydecimal(left_digits=2, right_digits=2, positive=True)))
    booked_daily_rate = factory.LazyAttribute(lambda o: getattr(o.motorcycle, 'daily_hire_rate', fake.pydecimal(left_digits=3, right_digits=2, positive=True)))

    total_hire_price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True))
    total_addons_price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    total_package_price = factory.LazyAttribute(lambda o: getattr(o.package, 'daily_cost', fake.pydecimal(left_digits=2, right_digits=2, positive=True)))

    grand_total = factory.LazyAttribute(
        lambda o: o.total_hire_price + o.total_addons_price + o.total_package_price
    )
    deposit_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    currency = 'AUD'


class HireBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HireBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    driver_profile = factory.SubFactory(DriverProfileFactory)
    package = factory.SubFactory(PackageFactory)
    payment = factory.SubFactory(PaymentFactory)

    @factory.post_generation
    def set_stripe_payment_intent_id(obj, create, extracted, **kwargs):
        if create and obj.payment and obj.payment.stripe_payment_intent_id:
            obj.stripe_payment_intent_id = obj.payment.stripe_payment_intent_id
            obj.save(update_fields=['stripe_payment_intent_id'])

    pickup_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    pickup_time = factory.Faker('time_object')
    return_date = factory.LazyAttribute(lambda o: o.pickup_date + datetime.timedelta(days=fake.random_int(min=1, max=7)))
    return_time = factory.Faker('time_object')

    booking_reference = factory.Sequence(lambda n: f"HIRE-{uuid.uuid4().hex[:8].upper()}")
    is_international_booking = factory.Faker('boolean')

    booked_hourly_rate = factory.LazyAttribute(lambda o: getattr(o.motorcycle, 'hourly_hire_rate', fake.pydecimal(left_digits=2, right_digits=2, positive=True)))
    booked_daily_rate = factory.LazyAttribute(lambda o: getattr(o.motorcycle, 'daily_hire_rate', fake.pydecimal(left_digits=3, right_digits=2, positive=True)))

    total_hire_price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True))
    total_addons_price = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    total_package_price = factory.LazyAttribute(lambda o: getattr(o.package, 'daily_cost', fake.pydecimal(left_digits=2, right_digits=2, positive=True)))
    grand_total = factory.LazyAttribute(
        lambda o: o.total_hire_price + o.total_addons_price + o.total_package_price
    )
    deposit_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    amount_paid = factory.LazyAttribute(lambda o: o.grand_total)
    payment_status = factory.Faker('random_element', elements=['pending', 'paid', 'requires_action', 'refunded', 'failed'])
    payment_method = factory.Faker('random_element', elements=['credit_card', 'bank_transfer', 'cash', 'stripe'])
    currency = 'AUD'

    status = factory.Faker('random_element', elements=['pending', 'confirmed', 'cancelled', 'completed', 'picked_up', 'returned'])
    customer_notes = factory.Faker('paragraph')
    internal_notes = factory.Faker('paragraph')


class BookingAddOnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BookingAddOn

    booking = factory.SubFactory(HireBookingFactory)
    addon = factory.SubFactory(AddOnFactory)

    quantity = factory.Faker('random_int', min=1, max=3)
    booked_addon_price = factory.LazyAttribute(lambda o: o.addon.daily_cost * o.quantity)


class RefundRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundRequest

    hire_booking = factory.SubFactory(HireBookingFactory)
    payment = factory.SubFactory(PaymentFactory)
    driver_profile = factory.SubFactory(DriverProfileFactory)

    reason = factory.Faker('paragraph')
    rejection_reason = None
    requested_at = factory.LazyFunction(timezone.now)
    status = factory.Faker('random_element', elements=['pending', 'approved', 'rejected', 'processed'])
    amount_to_refund = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    processed_by = None
    processed_at = None
    staff_notes = factory.Faker('paragraph')
    stripe_refund_id = factory.Sequence(lambda n: f"re_{uuid.uuid4().hex[:24]}_{n}")
    is_admin_initiated = factory.Faker('boolean')
    refund_calculation_details = factory.LazyFunction(
        lambda: {
            'policy_version': '1.0',
            'refunded_amount': str(fake.pydecimal(left_digits=2, right_digits=2, positive=True))
        }
    )
    request_email = factory.Faker('email')
    verification_token = factory.LazyFunction(uuid.uuid4)
    token_created_at = factory.LazyFunction(timezone.now)


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

class ServiceBrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBrand
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Brand {n}')


class ServiceTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceType

    name = factory.Sequence(lambda n: f'Service Type {n}')
    description = factory.Faker('paragraph')
    estimated_duration = factory.LazyFunction(
        lambda: datetime.timedelta(hours=fake.random_int(min=1, max=8))
    )
    base_price = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    is_active = True


class ServiceProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker('name')
    email = factory.LazyAttribute(lambda o: o.user.email if o.user else factory.Faker('email'))
    phone_number = factory.LazyFunction(lambda: fake.numerify('##########'))
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')

class CustomerMotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerMotorcycle

    service_profile = factory.SubFactory(ServiceProfileFactory)
    brand = factory.Faker('word', ext_word_list=['Honda', 'Yamaha', 'Kawasaki', 'Suzuki', 'Ducati', 'Harley-Davidson', 'Other'])
    model = factory.Faker('word')
    year = factory.LazyFunction(lambda: fake.year())
    engine_size = factory.Faker('numerify', text='###cc')
    rego = factory.Faker('bothify', text='???###')
    vin_number = factory.Faker('bothify', text='#################')
    odometer = factory.Faker('random_int', min=0, max=100000)
    transmission = factory.Faker('random_element', elements=[choice[0] for choice in CustomerMotorcycle.transmission_choices])
    engine_number = factory.Faker('bothify', text='######')

class BlockedServiceDateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockedServiceDate

    start_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    end_date = factory.LazyAttribute(lambda o: o.start_date + datetime.timedelta(days=fake.random_int(min=0, max=7)))
    description = factory.Faker('sentence')

class ServiceSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceSettings
        django_get_or_create = ('pk',)

    enable_service_booking = True
    booking_advance_notice = 1
    max_visible_slots_per_day = 6
    allow_anonymous_bookings = True
    allow_account_bookings = True
    booking_open_days = "Mon,Tue,Wed,Thu,Fri"
    drop_off_start_time = datetime.time(9, 0)
    drop_off_end_time = datetime.time(17, 0)
    drop_off_spacing_mins = 30
    max_advance_dropoff_days = 7
    latest_same_day_dropoff_time = datetime.time(12, 0)
    
    allow_after_hours_dropoff = False
    after_hours_dropoff_disclaimer = factory.Faker('paragraph', nb_sentences=3)

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
    cancellation_deposit_full_refund_days = 7
    cancel_deposit_max_refund_percentage = Decimal('1.00')
    cancellation_deposit_partial_refund_days = 3
    cancellation_deposit_partial_refund_percentage = Decimal('0.50')
    cancellation_deposit_minimal_refund_days = 1
    cancellation_deposit_minimal_refund_percentage = Decimal('0.00')
    refund_deducts_stripe_fee_policy = True
    stripe_fee_percentage_domestic = Decimal('0.0170')
    stripe_fee_fixed_domestic = Decimal('0.30')
    stripe_fee_percentage_international = Decimal('0.0350')
    stripe_fee_fixed_international = Decimal('0.30')

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
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory, service_profile=factory.SelfAttribute('..service_profile'))
    payment_option = factory.Faker('random_element', elements=[choice[0] for choice in TempServiceBooking.PAYMENT_METHOD_CHOICES])
    
    dropoff_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    dropoff_time = factory.Faker('time_object')
    
    service_date = factory.LazyAttribute(
        lambda o: o.dropoff_date + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )
    
    estimated_pickup_date = None
    customer_notes = factory.Faker('paragraph')
    calculated_deposit_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))


class ServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceBooking

    service_booking_reference = factory.Sequence(lambda n: f"SERVICE-{n:08d}")
    service_type = factory.SubFactory(ServiceTypeFactory)
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory(CustomerMotorcycleFactory, service_profile=factory.SelfAttribute('..service_profile'))
    payment_option = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.PAYMENT_METHOD_CHOICES])
    payment = factory.SubFactory(PaymentFactory)
    calculated_total = factory.LazyFunction(lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True))
    calculated_deposit_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    amount_paid = factory.LazyAttribute(lambda o: o.calculated_total)
    payment_status = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.PAYMENT_STATUS_CHOICES])
    payment_method = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.PAYMENT_METHOD_CHOICES])
    currency = 'AUD'
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")
    
    dropoff_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    dropoff_time = factory.Faker('time_object')
    
    service_date = factory.LazyAttribute(
        lambda o: o.dropoff_date + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )
    
    estimated_pickup_date = factory.LazyAttribute(lambda o: o.service_date + datetime.timedelta(days=fake.random_int(min=1, max=5)))
    
    booking_status = factory.Faker('random_element', elements=[choice[0] for choice in ServiceBooking.BOOKING_STATUS_CHOICES])
    customer_notes = factory.Faker('paragraph')

class TempBookingAddOnFactory(factory.django.DjangoModelFactory):
    """
    Factory for the TempBookingAddOn model.
    """
    class Meta:
        model = TempBookingAddOn

    temp_booking = factory.SubFactory(TempHireBookingFactory)
    addon = factory.SubFactory(AddOnFactory)
    quantity = factory.Faker('random_int', min=1, max=3)
    
    # Calculate the price based on the addon's cost and quantity
    booked_addon_price = factory.LazyAttribute(
        lambda o: (o.addon.daily_cost * o.quantity) if o.addon else Decimal('0.00')
    )

class RefundPolicySettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundPolicySettings
        django_get_or_create = ('pk',) # Ensure only one instance is created/updated

    # Full Payment Cancellation Policy
    cancellation_full_payment_full_refund_days = factory.Faker('random_int', min=5, max=10)
    cancellation_full_payment_partial_refund_days = factory.Faker('random_int', min=2, max=4)
    cancellation_full_payment_partial_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([25.00, 50.00, 75.00])))
    cancellation_full_payment_minimal_refund_days = factory.Faker('random_int', min=0, max=1)
    cancellation_full_payment_minimal_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([0.00, 10.00, 20.00])))

    # Deposit Cancellation Policy
    cancellation_deposit_full_refund_days = factory.Faker('random_int', min=5, max=10)
    cancellation_deposit_partial_refund_days = factory.Faker('random_int', min=2, max=4)
    cancellation_deposit_partial_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([25.00, 50.00, 75.00])))
    cancellation_deposit_minimal_refund_days = factory.Faker('random_int', min=0, max=1)
    cancellation_deposit_minimal_refund_percentage = factory.LazyFunction(lambda: Decimal(fake.random_element([0.00, 10.00, 20.00])))

    # Stripe Fee Settings
    refund_deducts_stripe_fee_policy = factory.Faker('boolean')
    stripe_fee_percentage_domestic = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.0170', '0.0180'])))
    stripe_fee_fixed_domestic = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.30', '0.40'])))
    stripe_fee_percentage_international = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.0350', '0.0390'])))
    stripe_fee_fixed_international = factory.LazyFunction(lambda: Decimal(fake.random_element(['0.30', '0.40'])))

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Enforce singleton pattern: always get or create the instance with pk=1
        obj, created = model_class.objects.get_or_create(pk=1, defaults=kwargs)
        if not created:
            # If it already exists, update its fields with the new kwargs
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        return obj