import factory
import datetime
import uuid
from faker import Faker

fake = Faker()
from inventory.models import (
    BlockedSalesDate,
    InventorySettings,
    Motorcycle,
    MotorcycleCondition,
    MotorcycleImage,
    SalesBooking,
    SalesProfile,
    SalesTerms,
    TempSalesBooking,
    Salesfaq,
    FeaturedMotorcycle,
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
from users.tests.test_helpers.model_factories import UserFactory
from payments.tests.test_helpers.model_factories import PaymentFactory


class MotorcycleConditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MotorcycleCondition
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"condition_{n}")
    display_name = factory.LazyAttribute(lambda o: fake.word().title())


class MotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Motorcycle

    title = factory.LazyAttribute(lambda o: f"{o.year} {o.brand} {o.model}")
    brand = factory.Faker(
        "word",
        ext_word_list=[
            "Honda",
            "Yamaha",
            "Kawasaki",
            "Suzuki",
            "Ducati",
            "Harley-Davidson",
        ],
    )
    model = factory.LazyAttribute(lambda o: fake.word().title())
    year = factory.Faker("year")
    price = factory.LazyFunction(
        lambda: fake.pydecimal(
            left_digits=5, right_digits=2, positive=True, min_value=5000
        )
    )
    quantity = 1

    vin_number = factory.Faker("bothify", text="#################")
    engine_number = factory.Faker("bothify", text="######")
    condition = ""

    odometer = factory.Faker("random_int", min=0, max=100000)
    engine_size = factory.Faker("random_int", min=50, max=1800)
    seats = factory.Faker("random_int", min=1, max=2)
    transmission = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in Motorcycle.TRANSMISSION_CHOICES],
    )
    description = factory.Faker("paragraph", nb_sentences=5)
    image = None
    rego = factory.Faker("bothify", text="???###")
    rego_exp = factory.LazyFunction(
        lambda: fake.date_between(start_date="+6m", end_date="+2y")
    )
    stock_number = factory.Sequence(lambda n: f"STK-{n:05d}")
    is_available = True
    warranty_years = factory.Faker("random_int", min=0, max=5)
    special_text = factory.Faker("text", max_nb_chars=25)
    on_special = False

    @factory.post_generation
    def conditions(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for condition_item in extracted:
                if isinstance(condition_item, MotorcycleCondition):
                    condition = condition_item
                else:
                    # Assume it's a string name
                    condition, _ = MotorcycleCondition.objects.get_or_create(
                        name=condition_item,
                        defaults={"display_name": condition_item.replace("_", " ").title()},
                    )
                obj.conditions.add(condition)


class MotorcycleImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MotorcycleImage

    motorcycle = factory.SubFactory(MotorcycleFactory)
    image = factory.django.ImageField(filename="test_motorcycle_image.jpg")


class InventorySettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InventorySettings
        django_get_or_create = ("pk",)

    enable_depositless_viewing = True
    enable_reservation_by_deposit = True
    deposit_amount = factory.LazyFunction(
        lambda: fake.pydecimal(
            left_digits=3, right_digits=2, positive=True, min_value=50, max_value=500
        )
    )
    deposit_lifespan_days = 5
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
    currency_code = "AUD"
    currency_symbol = "$"
    enable_viewing_for_enquiry = True

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
    email = factory.Faker("email")
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
    # payment = factory.SubFactory(PaymentFactory) # Removed to allow default amount_paid

    # amount_paid is handled by the model's default unless a payment is explicitly linked
    # amount_paid = factory.LazyFunction(
    #     lambda: fake.pydecimal(left_digits=2, right_digits=2, positive=True)
    # )
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


class BlockedSalesDateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockedSalesDate

    start_date = factory.LazyFunction(
        lambda: fake.date_between(start_date="today", end_date="+30d")
    )
    end_date = factory.LazyAttribute(
        lambda o: o.start_date + datetime.timedelta(days=fake.random_int(min=0, max=7))
    )
    description = factory.Faker("sentence")


class SalesfaqFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Salesfaq

    booking_step = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in Salesfaq.BOOKING_STEP_CHOICES],
    )
    question = factory.Faker("sentence", nb_words=6)
    answer = factory.Faker("paragraph", nb_sentences=3)
    is_active = True
    display_order = factory.Sequence(lambda n: n)


class FeaturedMotorcycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeaturedMotorcycle

    motorcycle = factory.SubFactory(MotorcycleFactory)
    category = factory.Faker(
        "random_element",
        elements=[choice[0] for choice in FeaturedMotorcycle.CATEGORY_CHOICES],
    )
    order = factory.Sequence(lambda n: n)


class SalesTermsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesTerms

    version_number = factory.Sequence(lambda n: n)
    content = factory.Faker("paragraph", nb_sentences=10)
    is_active = True
