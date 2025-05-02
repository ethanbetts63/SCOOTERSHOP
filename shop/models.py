from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from datetime import timedelta, time
import uuid
from datetime import timedelta # Import timedelta for duration field help text example

# Custom User model extending Django's AbstractUser with additional fields
class User(AbstractUser):
    # Contact information fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address_line_1 = models.CharField(max_length=100, blank=True, null=True)
    address_line_2 = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    post_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)

    # ID verification images
    # Changed from ImageField to FileField
    id_image = models.FileField(upload_to='user_ids/', blank=True, null=True)
    # Changed from ImageField to FileField
    international_id_image = models.FileField(upload_to='user_ids/international/', blank=True, null=True)

    # Add related_name to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions '
                  'granted to each of their groups.',
        related_name="core_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="core_user_permissions_set",
        related_query_name="user",
    )

    def __str__(self):
        return f"{self.username} ({self.get_full_name() or self.email})"

# Model for motorcycle conditions
class MotorcycleCondition(models.Model):
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=50)

    def __str__(self):
        return self.display_name

# Main motorcycle model representing inventory
class Motorcycle(models.Model):
    STATUS_CHOICES = [
        ('for_sale', 'For Sale'),
        ('sold', 'Sold'),
        ('for_hire', 'For Hire'),
        ('unavailable', 'Unavailable'),
    ]

    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('demo', 'Demo'),
        ('hire', 'Hire'),
    ]

    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('semi-auto', 'Semi-Automatic'),
    ]

    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Sale price (if applicable)")

    # Additional identification fields
    vin_number = models.CharField(max_length=50, blank=True, null=True, help_text="Vehicle Identification Number")
    engine_number = models.CharField(max_length=50, blank=True, null=True, help_text="Engine number/identifier")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="owned_motorcycles", null=True, blank=True)

    # Keep the original field for backwards compatibility / simple cases
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)

    # Field for multiple conditions (like 'Used', 'Hire')
    conditions = models.ManyToManyField(
        MotorcycleCondition,
        related_name='motorcycles',
        blank=True,
        help_text="Select all applicable conditions (e.g., Used, Hire)",
    )

    odometer = models.IntegerField(null=True, blank=True)
    engine_size = models.CharField(max_length=50)

    # Required fields for all motorcycles
    seats = models.IntegerField(
        help_text="Number of seats on the motorcycle",
    )

    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        help_text="Motorcycle transmission type"
    )

    description = models.TextField()
    # Changed from ImageField to FileField
    image = models.FileField(upload_to='motorcycles/', null=True, blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    is_available = models.BooleanField(default=True, help_text="Is this bike generally available for sale or in the active hire fleet?")
    rego = models.CharField(max_length=20, help_text="Registration number", null=True, blank=True)
    rego_exp = models.DateField(help_text="Registration expiration date", null=True, blank=True)
    stock_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    # Hire rates
    daily_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per day for hiring (if applicable)"
    )

    # New hire rate fields
    weekly_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per week for hiring (if applicable)"
    )

    monthly_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per month for hiring (if applicable)"
    )

    # Returns a string representation of the motorcycle
    def __str__(self):
        return f"{self.year} {self.brand} {self.model}"

    # Provides the URL to access this specific motorcycle
    def get_absolute_url(self):
        return reverse('motorcycle-detail', kwargs={'pk': self.pk})

    # Returns formatted string of all conditions
    def get_conditions_display(self):
        """Return a formatted string of all conditions"""
        if self.conditions.exists():
            return ", ".join([condition.display_name for condition in self.conditions.all()])
        elif self.condition:
             # Fall back to the old field if no conditions are set in the new field
            return dict(self.CONDITION_CHOICES).get(self.condition, self.condition).title()
        return "N/A" # Or some default if neither is set

    # Checks if the motorcycle is available for hire
    def is_for_hire(self):
        """Checks if 'Hire' is one of the conditions."""
        return self.conditions.filter(name='hire').exists()

# Model for storing additional motorcycle images
class MotorcycleImage(models.Model):
    motorcycle = models.ForeignKey(Motorcycle, on_delete=models.CASCADE, related_name='images')
    # Changed from ImageField to FileField
    image = models.FileField(upload_to='motorcycles/additional/')

    def __str__(self):
        return f"Image for {self.motorcycle}"

# Model for customers' personal motorcycles being serviced
class CustomerMotorcycle(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_motorcycles')
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    vin_number = models.CharField(max_length=50, blank=True, null=True)
    engine_number = models.CharField(max_length=50, blank=True, null=True)
    rego = models.CharField(max_length=20, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    # Added Odometer and Transmission based on service booking plan
    odometer = models.IntegerField(null=True, blank=True)
    transmission = models.CharField(
        max_length=20,
        choices=Motorcycle.TRANSMISSION_CHOICES, # Reference choices from Motorcycle
        blank=True,
        null=True,
        help_text="Customer motorcycle transmission type"
    )

    def __str__(self):
        return f"{self.year} {self.make} {self.model} (owned by {self.owner.get_full_name() or self.owner.username})"

# Model defining types of service offered
class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    estimated_duration = models.DurationField(help_text="Estimated time to complete this service")
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True, help_text="Whether this service is currently offered")
    # Changed from ImageField to FileField
    image = models.FileField(upload_to='service_types/', null=True, blank=True, help_text="Icon image for this service type")

    def __str__(self):
        return self.name

# Model for service appointments
class ServiceBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    CONTACT_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
    ]

    # Customer details (can be linked to user or anonymous)
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='service_bookings', null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True, help_text="For anonymous bookings")
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)

    # Added preferred contact method
    preferred_contact = models.CharField(max_length=10, choices=CONTACT_CHOICES, blank=True, null=True)


    # Vehicle details (link to CustomerMotorcycle for logged-in users or store details directly for anonymous)
    vehicle = models.ForeignKey(
        CustomerMotorcycle,
        on_delete=models.SET_NULL,
        related_name='service_bookings',
        null=True,
        blank=True,
        help_text="Customer's motorcycle to be serviced (if linked to an account)"
    )

    # Added fields for anonymous vehicle details
    anon_vehicle_make = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle Make for anonymous bookings")
    anon_vehicle_model = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle Model for anonymous bookings")
    anon_vehicle_year = models.IntegerField(blank=True, null=True, help_text="Vehicle Year for anonymous bookings")
    anon_vehicle_rego = models.CharField(max_length=20, blank=True, null=True, help_text="Vehicle Registration for anonymous bookings")
    anon_vehicle_odometer = models.IntegerField(blank=True, null=True, help_text="Vehicle Odometer for anonymous bookings")
    anon_vehicle_transmission = models.CharField(
        max_length=20,
        choices=Motorcycle.TRANSMISSION_CHOICES, # Reference choices from Motorcycle
        blank=True,
        null=True,
        help_text="Vehicle Transmission for anonymous bookings"
    )


    # Service details
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name='bookings')
    appointment_datetime = models.DateTimeField()
    customer_notes = models.TextField(blank=True, null=True, help_text="Notes from the customer")
    mechanic_notes = models.TextField(blank=True, null=True, help_text="Notes from the mechanic")

    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Cost breakdown
    parts_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"SRV-{uuid.uuid4().hex[:8].upper()}"

        # Update total cost if parts and labor are provided
        if self.parts_cost is not None and self.labor_cost is not None:
            self.total_cost = self.parts_cost + self.labor_cost
        elif self.parts_cost is not None: # Handle only parts cost provided
             self.total_cost = self.parts_cost
        elif self.labor_cost is not None: # Handle only labor cost provided
             self.total_cost = self.labor_cost
        else: # Ensure total_cost is None if both parts and labor are None
             self.total_cost = None

        super().save(*args, **kwargs)

    def __str__(self):
        customer_display = self.customer.get_full_name() if self.customer else self.customer_name
        vehicle_display = ""
        if self.vehicle:
            vehicle_display = f" for {self.vehicle}"
        elif self.anon_vehicle_make and self.anon_vehicle_model:
             vehicle_display = f" for {self.anon_vehicle_year or ''} {self.anon_vehicle_make} {self.anon_vehicle_model}"

        return f"Service: {self.service_type} for {customer_display}{vehicle_display} - {self.appointment_datetime.strftime('%Y-%m-%d %H:%M')} ({self.status})"

# Model for motorcycle hire bookings
class HireBooking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('deposit_paid', 'Deposit Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded'),
    ]

    motorcycle = models.ForeignKey(
        Motorcycle,
        on_delete=models.CASCADE,
        related_name='hire_bookings',
        limit_choices_to={'conditions__name': 'hire'}
    )

    customer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='hire_bookings',
        null=True,
        blank=True
    )

    # Changed from start_date/end_date to pickup/dropoff datetime
    pickup_datetime = models.DateTimeField(help_text="Pickup date and time")
    dropoff_datetime = models.DateTimeField(help_text="Dropoff date and time")

    # Booking financial details
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_weekly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_monthly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')

    # Booking metadata
    booking_reference = models.CharField(max_length=20, unique=True, blank=True)
    customer_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hire: {self.motorcycle} ({self.pickup_datetime.strftime('%Y-%m-%d')} to {self.dropoff_datetime.strftime('%Y-%m-%d')}) - {self.status}"

    class Meta:
        ordering = ['pickup_datetime', 'motorcycle']

class SiteSettings(models.Model):
    """
    Model for storing site-wide settings and configuration options
    """
# Visibility Fields - control which features are enabled on the site
    enable_sales_new = models.BooleanField(default=True, help_text="Enable new motorcycle sales")
    enable_sales_used = models.BooleanField(default=True, help_text="Enable used motorcycle sales")
    enable_hire = models.BooleanField(default=True, help_text="Enable motorcycle hire services")
    enable_service_booking = models.BooleanField(default=True, help_text="Enable service booking functionality")
    enable_user_accounts = models.BooleanField(default=True, help_text="Enable user account registration")
    enable_contact_page = models.BooleanField(default=True, help_text="Enable the contact us page")
    enable_about_page = models.BooleanField(default=True, help_text="Enable the about us page")
    enable_map_display = models.BooleanField(default=True, help_text="Enable displaying a map (e.g., location map)")
    enable_featured_section = models.BooleanField(default=True, help_text="Enable a featured items or content section")
    enable_privacy_policy_page = models.BooleanField(default=True, help_text="Enable the privacy policy page")
    enable_returns_page = models.BooleanField(default=True, help_text="Enable the returns page")
    enable_security_page = models.BooleanField(default=True, help_text="Enable the security page")
    enable_terms_page = models.BooleanField(default=True, help_text="Enable the terms and conditions page")


    # Service Booking Fields
    allow_anonymous_bookings = models.BooleanField(default=True, help_text="Allow service bookings without an account")
    allow_account_bookings = models.BooleanField(default=True, help_text="Allow service bookings with an account")
    booking_open_days = models.IntegerField(default=60, help_text="Number of days in advance that bookings can be made")
    booking_start_time = models.TimeField(default=time(9, 0), help_text="Earliest time of day for service bookings (e.g., 09:00)") # Added default
    booking_end_time = models.TimeField(default=time(17, 0), help_text="Latest time of day for service bookings (e.g., 17:00)") # Added default
    booking_advance_notice = models.IntegerField(default=1, help_text="Minimum number of days notice required for a booking")
    max_visible_slots_per_day = models.IntegerField(default=6, help_text="Maximum number of booking slots to show per day")
    service_confirmation_email_subject = models.CharField(max_length=200, default="Your service booking has been confirmed")
    service_pending_email_subject = models.CharField(max_length=200, default="Your service booking request has been received")
    admin_service_notification_email = models.EmailField(blank=True, null=True, help_text="Email address for service booking notifications")

    # Hire Booking Fields
    minimum_hire_duration_days = models.IntegerField(default=1, help_text="Minimum number of days for a hire booking")
    maximum_hire_duration_days = models.IntegerField(default=30, help_text="Maximum number of days for a hire booking")
    hire_booking_advance_notice = models.IntegerField(default=1, help_text="Minimum number of days notice required for a hire booking")
    default_hire_deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=25.00, help_text="Default deposit percentage for hire bookings")
    hire_confirmation_email_subject = models.CharField(max_length=200, default="Your motorcycle hire booking has been confirmed")
    admin_hire_notification_email = models.EmailField(blank=True, null=True, help_text="Email address for hire booking notifications")

    # Sales Fields
    display_new_prices = models.BooleanField(default=True, help_text="Display prices for new motorcycles")
    display_used_prices = models.BooleanField(default=True, help_text="Display prices for used motorcycles")

    # Business Fields
    phone_number = models.CharField(max_length=20, blank=True, null=True, default='(08) 9433 4613')
    email_address = models.EmailField(blank=True, null=True, default='admin@scootershop.com.au')
    storefront_address = models.TextField(blank=True, null=True, default='Unit 2/95 Queen Victoria St, Fremantle WA, Australia')

    # Business Hours
    opening_hours_monday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_tuesday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_wednesday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_thursday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_friday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_saturday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 1:00pm (By Appointment only)')
    opening_hours_sunday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='Closed')

    # System fields
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Site Settings"

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        """
        Ensure there is only ever one instance of SiteSettings
        """
        if not self.pk and SiteSettings.objects.exists():
            # if you're trying to create a new object but one already exists
            return
        return super(SiteSettings, self).save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """
        Returns the settings instance, creating it if necessary
        """
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    @classmethod
    def get_service_booking_settings(cls):
        """
        Returns the service booking related settings
        """
        settings = cls.get_settings()
        return {
            'allow_anonymous_bookings': settings.allow_anonymous_bookings,
            'allow_account_bookings': settings.allow_account_bookings,
            'booking_open_days': settings.booking_open_days,
            'booking_start_time': settings.booking_start_time,
            'booking_end_time': settings.booking_end_time,
            'booking_advance_notice': settings.booking_advance_notice,
            'max_visible_slots_per_day': settings.max_visible_slots_per_day,
        }

    @classmethod
    def get_hire_booking_settings(cls):
        """
        Returns the hire booking related settings
        """
        settings = cls.get_settings()
        return {
            'minimum_hire_duration_days': settings.minimum_hire_duration_days,
            'maximum_hire_duration_days': settings.maximum_hire_duration_days,
            'hire_booking_advance_notice': settings.hire_booking_advance_notice,
            'default_hire_deposit_percentage': settings.default_hire_deposit_percentage,
        }

    @classmethod
    def get_business_hours(cls):
        """
        Returns the business hours settings as a dictionary
        """
        settings = cls.get_settings()
        return {
            'monday': settings.opening_hours_monday,
            'tuesday': settings.opening_hours_tuesday,
            'wednesday': settings.opening_hours_wednesday,
            'thursday': settings.opening_hours_thursday,
            'friday': settings.opening_hours_friday,
            'saturday': settings.opening_hours_saturday,
            'sunday': settings.opening_hours_sunday,
        }

# Base model for page content
class PageContentBase(models.Model):
    """Base model for page content"""
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# Content for About page
class AboutPageContent(PageContentBase):
    intro_text = models.TextField(help_text="Introduction text at the top of the About page")
    sales_title = models.CharField(max_length=100, default="Sales")
    sales_content = models.TextField(help_text="Content for the Sales section")
    # Changed from ImageField to FileField
    sales_image = models.FileField(upload_to='about/', help_text="Image for the Sales section", null=True, blank=True) # Added blank=True

    service_title = models.CharField(max_length=100, default="Service")
    service_content = models.TextField(help_text="Content for the Service section")
    # Changed from ImageField to FileField
    service_image = models.FileField(upload_to='about/', help_text="Image for the Service section", null=True, blank=True) # Added blank=True

    parts_title = models.CharField(max_length=100, default="Parts & Accessories")
    parts_content = models.TextField(help_text="Content for the Parts & Accessories section")
    # Changed from ImageField to FileField
    parts_image = models.FileField(upload_to='about/', help_text="Image for the Parts section", null=True, blank=True) # Added blank=True

    cta_text = models.TextField(help_text="Call to action text at the bottom of the page")

    def __str__(self):
        return "About Page Content"

    class Meta:
        verbose_name = "About Page Content"
        verbose_name_plural = "About Page Content"