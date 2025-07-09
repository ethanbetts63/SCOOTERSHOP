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
from service.models import (
    ServiceBooking,
    ServiceProfile,
    TempServiceBooking,
    CustomerMotorcycle,
    ServiceBrand,
    ServiceType,
    BlockedServiceDate,
    ServiceSettings,
)
from inventory.models import (
    Motorcycle,
    MotorcycleCondition,
    SalesBooking,
    TempSalesBooking,
    SalesProfile,
)

from inventory.models.temp_sales_booking import (
    PAYMENT_STATUS_CHOICES as TEMP_PAYMENT_STATUS_CHOICES,
)
from inventory.models.temp_sales_booking import (
    BOOKING_STATUS_CHOICES as TEMP_BOOKING_STATUS_CHOICES,
)
from inventory.models.sales_booking import (
    PAYMENT_STATUS_CHOICES as SALES_PAYMENT_STATUS_CHOICES,
)
from inventory.models.sales_booking import (
    BOOKING_STATUS_CHOICES as SALES_BOOKING_STATUS_CHOICES,
)

User = get_user_model()


def get_model_choices(app_label, model_name, choices_attribute):

    django.apps.apps.check_apps_ready()
    model = django.apps.apps.get_model(app_label, model_name)
    return [choice[0] for choice in getattr(model, choices_attribute)]



class MotorcycleConditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MotorcycleCondition
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"condition_{n}")
    display_name = factory.LazyAttribute(lambda o: o.name.replace("_", " ").title())


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

    @factory.post_generation
    def conditions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for condition in extracted:
                self.conditions.add(condition)
        else:
            default_condition_name = fake.random_element(elements=["used"])
            condition_obj, _ = MotorcycleCondition.objects.get_or_create(
                name=default_condition_name,
                defaults={
                    "display_name": default_condition_name.replace("_", " ").title()
                },
            )
            self.conditions.add(condition_obj)

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


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    temp_service_booking = None
    service_booking = None
    service_customer_profile = None
    temp_sales_booking = None
    sales_booking = factory.RelatedFactory("payments.tests.test_helpers.model_factories.SalesBookingFactory", 'payment')
    sales_customer_profile = None

    stripe_payment_intent_id = factory.Sequence(
        lambda n: f"pi_{uuid.uuid4().hex[:24]}_{n}"
    )
    stripe_payment_method_id = factory.Faker("md5")
    amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    currency = "AUD"

    status = factory.Faker(
        "random_element",
        elements=[
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "succeeded",
            "canceled",
            "failed",
        ],
    )
    description = factory.Faker("sentence")

    metadata = factory.LazyFunction(dict)

    refund_policy_snapshot = factory.LazyFunction(
        lambda: {
            "policy_version": "1.0",
            "deduct_fees": True,
            "sales_enable_deposit_refund_grace_period": fake.boolean(),
            "sales_deposit_refund_grace_period_hours": fake.random_int(min=12, max=72),
            "sales_enable_deposit_refund": fake.boolean(),
        }
    )
    refunded_amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    )


class WebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    stripe_event_id = factory.Sequence(lambda n: f"evt_{uuid.uuid4().hex[:24]}_{n}")
    event_type = factory.Faker(
        "random_element",
        elements=[
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "charge.refunded",
            "customer.created",
            "checkout.session.completed",
        ],
    )
    received_at = factory.LazyFunction(timezone.now)
    payload = factory.LazyFunction(
        lambda: fake.json(num_rows=1, data_columns={"key": "text", "value": "text"})
    )


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
    staff_notes = factory.Faker("paragraph")
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


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'testpassword')
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

class StaffUserFactory(UserFactory):
    is_staff = True

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

    enable_deposit = False
    deposit_calc_method = "FLAT_FEE"
    deposit_flat_fee_amount = Decimal("0.00")
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
    payment_method = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in TempServiceBooking.PAYMENT_METHOD_CHOICES],
    )

    dropoff_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+30d")
    )
    dropoff_time = factory.Faker("time_object")

    service_date = factory.LazyAttribute(
        lambda o: o.dropoff_date
        + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )

    estimated_pickup_date = None
    customer_notes = factory.Faker("paragraph")
    calculated_deposit_amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    )


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


class RefundPolicySettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RefundPolicySettings

    cancellation_full_payment_full_refund_days = factory.Faker(
        "random_int", min=5, max=10
    )
    cancellation_full_payment_partial_refund_days = factory.Faker(
        "random_int", min=2, max=4
    )
    cancellation_full_payment_partial_refund_percentage = factory.LazyFunction(
        lambda: Decimal(fake.random_element([25.00, 50.00, 75.00]))
    )
    cancellation_full_payment_minimal_refund_days = factory.Faker(
        "random_int", min=0, max=1
    )
    cancellation_full_payment_minimal_refund_percentage = factory.LazyFunction(
        lambda: Decimal(fake.random_element([0.00, 10.00, 20.00]))
    )

    cancellation_deposit_full_refund_days = factory.Faker("random_int", min=5, max=10)
    cancellation_deposit_partial_refund_days = factory.Faker("random_int", min=2, max=4)
    cancellation_deposit_partial_refund_percentage = factory.LazyFunction(
        lambda: Decimal(fake.random_element([25.00, 50.00, 75.00]))
    )
    cancellation_deposit_minimal_refund_days = factory.Faker("random_int", min=0, max=1)
    cancellation_deposit_minimal_refund_percentage = factory.LazyFunction(
        lambda: Decimal(fake.random_element([0.00, 10.00, 20.00]))
    )

    sales_enable_deposit_refund_grace_period = factory.Faker("boolean")
    sales_deposit_refund_grace_period_hours = factory.Faker(
        "random_int", min=12, max=72
    )
    sales_enable_deposit_refund = factory.Faker("boolean")

    refund_deducts_stripe_fee_policy = factory.Faker("boolean")
    stripe_fee_percentage_domestic = factory.LazyFunction(
        lambda: Decimal(fake.random_element(["0.0170", "0.0180"]))
    )
    stripe_fee_fixed_domestic = factory.LazyFunction(
        lambda: Decimal(fake.random_element(["0.30", "0.40"]))
    )
    stripe_fee_percentage_international = factory.LazyFunction(
        lambda: Decimal(fake.random_element(["0.0350", "0.0390"]))
    )
    stripe_fee_fixed_international = factory.LazyFunction(
        lambda: Decimal(fake.random_element(["0.30", "0.40"]))
    )

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


class TempSalesBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TempSalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory)

    amount_paid = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    )
    payment_status = factory.Faker(
        "random_element", elements=[choice[0] for choice in TEMP_PAYMENT_STATUS_CHOICES]
    )
    currency = "AUD"
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+30d")
    )
    appointment_time = factory.Faker("time_object")

    customer_notes = factory.Faker("paragraph")

    booking_status = factory.Faker(
        "random_element", elements=[choice[0] for choice in TEMP_BOOKING_STATUS_CHOICES]
    )
    deposit_required_for_flow = factory.Faker("boolean")

class SalesBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesBooking

    motorcycle = factory.SubFactory(MotorcycleFactory)
    sales_profile = factory.SubFactory(SalesProfileFactory)
    payment = factory.SubFactory(PaymentFactory)

    sales_booking_reference = factory.Sequence(
        lambda n: f"SBK-{uuid.uuid4().hex[:8].upper()}"
    )
    amount_paid = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    )
    payment_status = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in SALES_PAYMENT_STATUS_CHOICES],
    )
    currency = "AUD"
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_{uuid.uuid4().hex[:24]}")

    appointment_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+60d")
    )
    appointment_time = factory.Faker("time_object")

    booking_status = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in SALES_BOOKING_STATUS_CHOICES],
    )
    customer_notes = factory.Faker("paragraph")
