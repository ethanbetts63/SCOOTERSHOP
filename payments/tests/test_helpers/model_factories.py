import factory
import datetime
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from faker import Faker
import django.apps # Import django.apps

fake = Faker()


# Payments app models
from payments.models import Payment, WebhookEvent, HireRefundRequest
from hire.models import TempHireBooking, HireBooking, DriverProfile, BookingAddOn, Package, AddOn
from service.models import ServiceBooking, ServiceProfile, TempServiceBooking
from inventory.models import Motorcycle, MotorcycleCondition

# Get Django's User model
User = get_user_model()


# Helper function to get model choices safely
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
    status = factory.Faker('random_element', elements=factory.LazyFunction(lambda: [choice[0] for choice in Payment.STATUS_CHOICES]))
    description = factory.Faker('sentence')
    metadata = factory.LazyFunction(lambda: {'test_key': fake.word()})
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
    payment_option = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('hire', 'TempHireBooking', 'PAYMENT_METHOD_CHOICES')))

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
    payment_status = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('hire', 'HireBooking', 'PAYMENT_STATUS_CHOICES')))
    payment_method = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('hire', 'HireBooking', 'PAYMENT_METHOD_CHOICES')))
    currency = 'AUD'

    status = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('hire', 'HireBooking', 'STATUS_CHOICES')))
    customer_notes = factory.Faker('paragraph')
    internal_notes = factory.Faker('paragraph')


class BookingAddOnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BookingAddOn

    booking = factory.SubFactory(HireBookingFactory)
    addon = factory.SubFactory(AddOnFactory)

    quantity = factory.Faker('random_int', min=1, max=3)
    booked_addon_price = factory.LazyAttribute(lambda o: o.addon.daily_cost * o.quantity)


class HireRefundRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HireRefundRequest

    hire_booking = factory.SubFactory(HireBookingFactory)
    payment = factory.SubFactory(PaymentFactory)
    driver_profile = factory.SubFactory(DriverProfileFactory)

    reason = factory.Faker('paragraph')
    rejection_reason = None
    requested_at = factory.LazyFunction(timezone.now)
    status = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('payments', 'HireRefundRequest', 'STATUS_CHOICES')))
    amount_to_refund = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    processed_by = None
    processed_at = None
    staff_notes = factory.Faker('paragraph')
    stripe_refund_id = factory.Sequence(lambda n: f"re_{uuid.uuid4().hex[:24]}_{n}")
    is_admin_initiated = factory.Faker('boolean')
    refund_calculation_details = factory.LazyFunction(lambda: {'policy_version': '1.0', 'refunded_amount': fake.pydecimal(left_digits=2, right_digits=2)})
    request_email = factory.Faker('email')
    verification_token = factory.LazyFunction(uuid.uuid4)
    token_created_at = factory.LazyFunction(timezone.now)


class ServiceProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProfile

    user = None
    name = factory.Faker('name')
    email = factory.Faker('email')
    phone_number = factory.LazyFunction(lambda: fake.numerify('##########'))
    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    post_code = factory.Faker('postcode')
    country = factory.Faker('country_code')


class TempServiceBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TempServiceBooking

    session_uuid = factory.LazyFunction(uuid.uuid4)
    service_type = factory.SubFactory('service.ServiceType')
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory('service.CustomerMotorcycle', service_profile=factory.SelfAttribute('..service_profile'))
    payment_option = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('service', 'TempServiceBooking', 'PAYMENT_METHOD_CHOICES')))

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
    service_type = factory.SubFactory('service.ServiceType')
    service_profile = factory.SubFactory(ServiceProfileFactory)
    customer_motorcycle = factory.SubFactory('service.CustomerMotorcycle', service_profile=factory.SelfAttribute('..service_profile'))
    payment_option = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('service', 'ServiceBooking', 'PAYMENT_METHOD_CHOICES')))
    payment = factory.SubFactory(PaymentFactory)

    calculated_total = factory.LazyFunction(lambda: fake.pydecimal(left_digits=4, right_digits=2, positive=True))
    calculated_deposit_amount = factory.LazyFunction(lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True))
    amount_paid = factory.LazyAttribute(lambda o: o.calculated_total)
    payment_status = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('service', 'ServiceBooking', 'PAYMENT_STATUS_CHOICES')))
    payment_method = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('service', 'ServiceBooking', 'PAYMENT_METHOD_CHOICES')))
    currency = 'AUD'

    stripe_payment_intent_id = factory.LazyAttribute(lambda o: o.payment.stripe_payment_intent_id if o.payment else None)

    dropoff_date = factory.LazyFunction(lambda: fake.date_between(start_date='today', end_date='+30d'))
    dropoff_time = factory.Faker('time_object')

    service_date = factory.LazyAttribute(
        lambda o: o.dropoff_date + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )

    estimated_pickup_date = factory.LazyAttribute(lambda o: o.service_date + datetime.timedelta(days=fake.random_int(min=1, max=5)))

    booking_status = factory.Faker('random_element', elements=factory.LazyFunction(lambda: get_model_choices('service', 'ServiceBooking', 'BOOKING_STATUS_CHOICES')))
    customer_notes = factory.Faker('paragraph')
