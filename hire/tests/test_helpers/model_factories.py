# hire/tests/test_helpers/model_factories.py

import datetime
from decimal import Decimal
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model

# Import models from their respective apps
from inventory.models import Motorcycle, MotorcycleCondition
from payments.models import Payment
from dashboard.models import HireSettings

# Import models from the current 'hire' app
from hire.models import (
    DriverProfile,
    AddOn,
    Package,
    HireBooking,
    BookingAddOn,
    TempHireBooking,
    TempBookingAddOn
)

User = get_user_model() # Get the custom User model

# --- Helper for creating common related models ---

def create_user(username, password="password123", email=None):
    """Creates a Django User instance."""
    if not email:
        email = f"{username}@example.com"
    return User.objects.create_user(username=username, password=password, email=email)

def create_motorcycle_condition(name, display_name):
    """Creates a MotorcycleCondition instance."""
    return MotorcycleCondition.objects.get_or_create(name=name, defaults={'display_name': display_name})[0]

def create_motorcycle(
    title="Standard Hire Bike",
    brand="Honda",
    model="CBR500R",
    year=2023,
    odometer=1000,
    engine_size=500,
    daily_hire_rate=Decimal('100.00'),
    hourly_hire_rate=Decimal('20.00'),
    is_available=True, # Default to True for hire bikes
    rego="ABC123",
    rego_exp=None,
    stock_number=None,
    price=None,
    vin_number=None,
    engine_number=None,
    owner=None,
    seats=2,
    transmission='manual',
    description="A reliable and fun motorcycle for hire.",
    image=None,
):
    """
    Creates a Motorcycle instance, specifically configured as a hire bike,
    with appropriate default values.
    """
    if not rego_exp:
        rego_exp = timezone.now().date() + datetime.timedelta(days=365)
    if not stock_number:
        stock_number = f"STK-{uuid.uuid4().hex[:8].upper()}"

    motorcycle = Motorcycle.objects.create(
        title=title,
        brand=brand,
        model=model,
        year=year,
        odometer=odometer,
        engine_size=engine_size,
        daily_hire_rate=daily_hire_rate,
        hourly_hire_rate=hourly_hire_rate,
        is_available=is_available,
        rego=rego,
        rego_exp=rego_exp,
        stock_number=stock_number,
        price=price,
        vin_number=vin_number,
        engine_number=engine_number,
        owner=owner,
        seats=seats,
        transmission=transmission,
        description=description,
        image=image,
    )

    # Always add the 'hire' condition, as requested
    hire_condition = create_motorcycle_condition(name='hire', display_name='For Hire')
    motorcycle.conditions.add(hire_condition)

    return motorcycle

def create_hire_settings(
    minimum_hire_duration_hours=2,
    maximum_hire_duration_days=30,
    booking_lead_time_hours=2,
    pick_up_start_time=datetime.time(9, 0),
    pick_up_end_time=datetime.time(17, 0),
    return_off_start_time=datetime.time(9, 0),
    return_end_time=datetime.time(17, 0),
    currency_symbol='$',
    currency_code='AUD',
    minimum_driver_age=18,
    deposit_enabled=False,
    default_deposit_calculation_method='percentage',
    deposit_percentage=Decimal('10.00'),
    deposit_amount=Decimal('50.00'),
    default_daily_rate=Decimal('90.00'),
    default_hourly_rate=Decimal('15.00'),
    enable_online_full_payment=False,
    enable_online_deposit_payment=False,
    enable_in_store_full_payment=False,
    packages_enabled=True,
    add_ons_enabled=True,
    # NEW: Add hire pricing strategy fields
    hire_pricing_strategy='24_hour_customer_friendly', # Default to a sensible option
    excess_hours_margin=2, # Default margin
):
    """Creates or gets a HireSettings instance."""
    settings, created = HireSettings.objects.get_or_create(pk=1) # Assuming pk=1 for singleton
    settings.minimum_hire_duration_hours = minimum_hire_duration_hours
    settings.maximum_hire_duration_days = maximum_hire_duration_days
    settings.booking_lead_time_hours = booking_lead_time_hours
    settings.pick_up_start_time = pick_up_start_time
    settings.pick_up_end_time = pick_up_end_time
    settings.return_off_start_time = return_off_start_time
    settings.return_end_time = return_end_time
    settings.currency_symbol = currency_symbol
    settings.currency_code = currency_code
    settings.minimum_driver_age = minimum_driver_age
    settings.deposit_enabled = deposit_enabled
    settings.default_deposit_calculation_method = default_deposit_calculation_method
    settings.deposit_percentage = deposit_percentage
    settings.deposit_amount = deposit_amount
    settings.default_daily_rate = default_daily_rate
    settings.default_hourly_rate = default_hourly_rate
    settings.enable_online_full_payment = enable_online_full_payment
    settings.enable_online_deposit_payment = enable_online_deposit_payment
    settings.enable_in_store_full_payment = enable_in_store_full_payment
    settings.packages_enabled = packages_enabled
    settings.add_ons_enabled = add_ons_enabled
    # NEW: Assign the new pricing strategy fields
    settings.hire_pricing_strategy = hire_pricing_strategy
    settings.excess_hours_margin = excess_hours_margin
    settings.save()
    return settings

def create_payment(
    amount=Decimal('100.00'),
    currency='AUD',
    status='pending',
    stripe_payment_intent_id=None,
    stripe_payment_method_id=None,
    # Add description and related booking/driver profile fields
    description=None,
    temp_hire_booking=None,
    hire_booking=None,
    driver_profile=None,
):
    """Creates a Payment instance."""
    return Payment.objects.create(
        amount=amount,
        currency=currency,
        status=status,
        stripe_payment_intent_id=stripe_payment_intent_id,
        stripe_payment_method_id=stripe_payment_method_id,
        description=description, # Pass description
        temp_hire_booking=temp_hire_booking, # Pass temp_hire_booking
        hire_booking=hire_booking, # Pass hire_booking
        driver_profile=driver_profile, # Pass driver_profile
    )

# --- Factories for Hire App Models ---

def create_driver_profile(
    user=None,
    name="John Doe",
    email="john.doe@example.com",
    phone_number="0412345678",
    address_line_1="123 Main St",
    city="Sydney",
    country="Australia",
    date_of_birth=None,
    is_australian_resident=True,
    license_number="123456789",
    license_expiry_date=None, # Main license expiry
    international_license_issuing_country="",
    international_license_expiry_date=None, # International license expiry
    passport_number="",
    passport_expiry_date=None, # Passport expiry
    license_photo=None,
    international_license_photo=None,
    passport_photo=None,
    id_image=None,
    international_id_image=None,
    # Add a flag to control default expiry dates for testing purposes
    _set_default_expiry_dates=True,
):
    """Creates a DriverProfile instance."""
    # Default date_of_birth if not provided
    if not date_of_birth:
        try:
            min_age = HireSettings.objects.first().minimum_driver_age
        except (HireSettings.DoesNotExist, AttributeError):
            min_age = 18 # Fallback default
        date_of_birth = timezone.now().date() - datetime.timedelta(days=(min_age + 4) * 365)

    # Default license_expiry_date (for the primary license) if not provided.
    # This is always required by the model, so it should always have a default.
    if license_expiry_date is None:
        license_expiry_date = timezone.now().date() + datetime.timedelta(days=365)

    # Set defaults for international/passport details if foreigner and not provided,
    # but only if _set_default_expiry_dates is True.
    if not is_australian_resident and _set_default_expiry_dates:
        if international_license_expiry_date is None:
            international_license_expiry_date = timezone.now().date() + datetime.timedelta(days=365)
        if passport_expiry_date is None:
            passport_expiry_date = timezone.now().date() + datetime.timedelta(days=365)
    # For Australian residents, international and passport fields should typically be None/empty
    # unless specific test data is being provided. The factory defaults them to empty/None.

    return DriverProfile.objects.create(
        user=user,
        name=name,
        email=email,
        phone_number=phone_number,
        address_line_1=address_line_1,
        city=city,
        country=country,
        date_of_birth=date_of_birth,
        is_australian_resident=is_australian_resident,
        license_number=license_number,
        license_expiry_date=license_expiry_date, # Now always has a value
        international_license_issuing_country=international_license_issuing_country,
        international_license_expiry_date=international_license_expiry_date,
        passport_number=passport_number,
        passport_expiry_date=passport_expiry_date,
        license_photo=license_photo,
        international_license_photo=international_license_photo,
        passport_photo=passport_photo,
        id_image=id_image,
        international_id_image=international_id_image,
    )

def create_addon(
    name="Helmet",
    description="Standard safety helmet",
    hourly_cost=Decimal('2.00'), # Changed from 'cost'
    daily_cost=Decimal('10.00'), # New field
    min_quantity=1,
    max_quantity=5,
    is_available=True
):
    """Creates an AddOn instance."""
    # Ensure hourly_cost and daily_cost are Decimal, defaulting to 0 if None is passed
    hourly_cost = hourly_cost if hourly_cost is not None else Decimal('0.00')
    daily_cost = daily_cost if daily_cost is not None else Decimal('0.00')

    return AddOn.objects.create(
        name=name,
        description=description,
        hourly_cost=hourly_cost, # Changed
        daily_cost=daily_cost,   # New
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        is_available=is_available
    )

def create_package(
    name="Adventure Pack",
    description="Includes helmet, jacket, and gloves",
    hourly_cost=Decimal('10.00'), # Changed from 'package_price'
    daily_cost=Decimal('50.00'), # New field
    add_ons=None, # List of AddOn instances
    is_available=True
):
    """Creates a Package instance."""
    # Ensure hourly_cost and daily_cost are Decimal, defaulting to 0 if None is passed
    hourly_cost = hourly_cost if hourly_cost is not None else Decimal('0.00')
    daily_cost = daily_cost if daily_cost is not None else Decimal('0.00')

    package = Package.objects.create(
        name=name,
        description=description,
        hourly_cost=hourly_cost, # Changed
        daily_cost=daily_cost,   # New
        is_available=is_available
    )
    if add_ons:
        package.add_ons.set(add_ons)
    return package

def create_hire_booking(
    motorcycle=None,
    driver_profile=None,
    pickup_date=None,
    pickup_time=None,
    return_date=None,
    return_time=None,
    booking_reference=None,
    is_international_booking=False,
    booked_hourly_rate=Decimal('20.00'),
    booked_daily_rate=Decimal('100.00'),
    total_hire_price=Decimal('160.00'),
    total_addons_price=Decimal('40.00'),
    total_package_price=Decimal('0.00'),
    grand_total=Decimal('200.00'),
    deposit_amount=Decimal('0.00'),
    amount_paid=Decimal('0.00'),
    payment_status='unpaid',
    payment_method='at_desk',
    status='pending',
    package=None,
    currency='AUD',
    payment=None,
    stripe_payment_intent_id=None,
    customer_notes="",
    internal_notes="",
):
    """Creates a HireBooking instance."""
    if not motorcycle:
        motorcycle = create_motorcycle()
    if not driver_profile:
        driver_profile = create_driver_profile()
    if not pickup_date:
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
    if not pickup_time:
        pickup_time = datetime.time(10, 0)
    if not return_date:
        return_date = pickup_date + datetime.timedelta(days=2)
    if not return_time:
        return_time = datetime.time(16, 0)
    if not booking_reference:
        booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"

    booking = HireBooking.objects.create(
        motorcycle=motorcycle,
        driver_profile=driver_profile,
        pickup_date=pickup_date,
        pickup_time=pickup_time,
        return_date=return_date,
        return_time=return_time,
        booking_reference=booking_reference,
        is_international_booking=is_international_booking,
        booked_hourly_rate=booked_hourly_rate,
        booked_daily_rate=booked_daily_rate,
        total_hire_price=total_hire_price,
        total_addons_price=total_addons_price,
        total_package_price=total_package_price,
        grand_total=grand_total,
        deposit_amount=deposit_amount,
        amount_paid=amount_paid,
        payment_status=payment_status,
        payment_method=payment_method,
        status=status,
        package=package,
        currency=currency,
        payment=payment,
        stripe_payment_intent_id=stripe_payment_intent_id,
        customer_notes=customer_notes,
        internal_notes=internal_notes,
    )
    return booking

def create_booking_addon(
    booking,
    addon=None,
    quantity=1,
    booked_addon_price=None # This will now represent the total addon price for the booking
):
    """Creates a BookingAddOn instance."""
    if not addon:
        addon = create_addon()
    # If booked_addon_price is not provided, use addon's daily_cost as a default.
    # The actual calculation (daily vs hourly, quantity) will happen in utils.
    if booked_addon_price is None:
        booked_addon_price = addon.daily_cost * quantity # Default to daily cost * quantity

    return BookingAddOn.objects.create(
        booking=booking,
        addon=addon,
        quantity=quantity,
        booked_addon_price=booked_addon_price
    )

def create_temp_hire_booking(
    session_uuid=None,
    pickup_date=None,
    pickup_time=None,
    return_date=None,
    return_time=None,
    has_motorcycle_license=False,
    motorcycle=None,
    package=None,
    driver_profile=None,
    is_international_booking=False,
    payment_option='online_full',
    booked_daily_rate=None,
    booked_hourly_rate=None, # Added this to match TempHireBooking model
    total_hire_price=None,
    total_addons_price=Decimal('0.00'),
    total_package_price=Decimal('0.00'),
    grand_total=None,
    deposit_amount=None,
    currency='AUD',
):
    """Creates a TempHireBooking instance."""
    if not session_uuid:
        session_uuid = uuid.uuid4()
    if not pickup_date:
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
    if not pickup_time:
        pickup_time = datetime.time(10, 0)
    if not return_date:
        return_date = pickup_date + datetime.timedelta(days=2)
    if not return_time:
        return_time = datetime.time(16, 0)
    if motorcycle and not booked_daily_rate:
        booked_daily_rate = motorcycle.daily_hire_rate
    if motorcycle and not booked_hourly_rate: # Added this
        booked_hourly_rate = motorcycle.hourly_hire_rate # Added this
    
    # If package is provided, set a default for total_package_price if not already set
    if package and total_package_price is None:
        total_package_price = package.daily_cost # Using daily_cost as a sensible default for factory

    temp_booking = TempHireBooking.objects.create(
        session_uuid=session_uuid,
        pickup_date=pickup_date,
        pickup_time=pickup_time,
        return_date=return_date,
        return_time=return_time,
        has_motorcycle_license=has_motorcycle_license,
        motorcycle=motorcycle,
        package=package,
        driver_profile=driver_profile,
        is_international_booking=is_international_booking,
        payment_option=payment_option,
        booked_daily_rate=booked_daily_rate,
        booked_hourly_rate=booked_hourly_rate, # Added this
        total_hire_price=total_hire_price,
        total_addons_price=total_addons_price,
        total_package_price=total_package_price,
        grand_total=grand_total,
        deposit_amount=deposit_amount,
        currency=currency,
    )
    return temp_booking

def create_temp_booking_addon(
    temp_booking,
    addon=None,
    quantity=1,
    booked_addon_price=None # This will now represent the total addon price for the temp booking
):
    """Creates a TempBookingAddOn instance."""
    if not addon:
        addon = create_addon()
    # If booked_addon_price is not provided, use addon's daily_cost as a default.
    # The actual calculation (daily vs hourly, quantity) will happen in utils.
    if booked_addon_price is None:
        booked_addon_price = addon.daily_cost * quantity # Default to daily cost * quantity

    return TempBookingAddOn.objects.create(
        temp_booking=temp_booking,
        addon=addon,
        quantity=quantity,
        booked_addon_price=booked_addon_price
    )
