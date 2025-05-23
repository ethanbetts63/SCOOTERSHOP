from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import datetime

from inventory.models import Motorcycle
from .driver_profile import DriverProfile
from dashboard.models import HireSettings
# Import the Payment model from the payments app
from payments.models import Payment


# Choices for booking status
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('cancelled', 'Cancelled'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('no_show', 'No Show'),
]

# Choices for payment status
PAYMENT_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('deposit_paid', 'Deposit Paid'),
    ('paid', 'Fully Paid'),
    ('refunded', 'Refunded'),
]

# Choices for payment method
PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('card', 'Card'),
    ('online', 'Online'),
    ('at_desk', 'At Desk (Pending Payment)'),
    ('other', 'Other')
]


class HireBooking(models.Model):
    # Relationships
    motorcycle = models.ForeignKey(
        Motorcycle,
        on_delete=models.CASCADE,
        related_name='hire_bookings',
        limit_choices_to={'conditions__name': 'hire'}
    )
    driver_profile = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='hire_bookings'
    )
    package = models.ForeignKey(
        'Package', # Using string literal as Package is in another file
        on_delete=models.SET_NULL,
        related_name='hire_bookings',
        null=True, blank=True
    )

    # Add a OneToOneField to the Payment model for robust linking
    # This ensures that each HireBooking corresponds to exactly one Payment record
    # and makes it easy to retrieve the HireBooking from a Payment Intent ID.
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL, # If payment record is deleted, don't delete booking
        related_name='hire_booking',
        null=True, blank=True, # Allow null initially, will be set upon successful payment
        help_text="Link to the associated payment record."
    )

    # Add a field to store the Stripe Payment Intent ID directly
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True, # Ensure uniqueness for this ID
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent associated with this booking."
    )

    # Package price at booking time
    booked_package_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Price of the selected package at the time of booking."
    )

    # Add-ons through intermediate model
    add_ons = models.ManyToManyField(
        'AddOn', # Using string literal as AddOn is in another file
        through='BookingAddOn',
        related_name='hire_bookings',
        blank=True
    )

    # Booking Dates and Times
    pickup_date = models.DateField(help_text="Pickup date")
    pickup_time = models.TimeField(help_text="Pickup time")
    return_date = models.DateField(help_text="Return date")
    return_time = models.TimeField(help_text="Return time")

    # Identifiers and Flags
    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    # Indicates if booking requires international documentation/considerations
    is_international_booking = models.BooleanField(default=False)

    # Financial Details
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_weekly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_monthly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, help_text="Method by which the payment was made.")
    
    # Currency of the booking (NEW FIELD)
    currency = models.CharField(
        max_length=3,
        default='AUD', 
        help_text="The three-letter ISO currency code for the booking."
    )

    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    customer_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hire: {self.motorcycle} ({self.pickup_date} to {self.return_date}) - {self.status}"

    def clean(self):
        """
        Custom validation for HireBooking data.
        """
        super().clean()

        errors = {}
        now = timezone.now()

        # --- Date and Time Validation ---
        pickup_datetime = None
        return_datetime = None

        if self.pickup_date and self.pickup_time:
            pickup_datetime = timezone.make_aware(datetime.datetime.combine(self.pickup_date, self.pickup_time))

        if self.return_date and self.return_time:
            return_datetime = timezone.make_aware(datetime.datetime.combine(self.return_date, self.return_time))

        if pickup_datetime and return_datetime:
            if return_datetime <= pickup_datetime:
                errors['return_date'] = "Return date and time must be after pickup date and time."
                errors['return_time'] = "Return date and time must be after pickup date and time."

            # Check minimum hire duration against settings
            try:
                settings = HireSettings.objects.first()
                if settings and settings.minimum_hire_duration_days is not None:
                    min_duration = datetime.timedelta(days=settings.minimum_hire_duration_days)
                    if (return_datetime - pickup_datetime) < min_duration:
                        errors['return_date'] = f"Hire duration must be at least {settings.minimum_hire_duration_days} days."
                        errors['return_time'] = f"Hire duration must be at least {settings.minimum_hire_duration_days} days."
            except HireSettings.DoesNotExist:
                # Handle missing settings if necessary
                pass
            except Exception as e:
                print(f"Error checking minimum hire duration: {e}")
                pass

        if pickup_datetime:
            # Check booking lead time against settings
            try:
                settings = HireSettings.objects.first()
                if settings and settings.booking_lead_time_hours is not None:
                    min_pickup_time = now + datetime.timedelta(hours=settings.booking_lead_time_hours)
                    if pickup_datetime < min_pickup_time:
                        errors['pickup_date'] = f"Pickup must be at least {settings.booking_lead_time_hours} hours from now."
                        errors['pickup_time'] = f"Pickup must be at least {settings.booking_lead_time_hours} hours from now."
            except HireSettings.DoesNotExist:
                # Handle missing settings if necessary
                pass
            except Exception as e:
                print(f"Error checking booking lead time: {e}")
                pass


        # --- Financial Validation ---
        if self.total_price is not None and self.total_price < 0:
            errors['total_price'] = "Total price cannot be negative."
        if self.deposit_amount is not None and self.deposit_amount < 0:
            errors['deposit_amount'] = "Deposit amount cannot be negative."
        if self.amount_paid is not None and self.amount_paid < 0:
            errors['amount_paid'] = "Amount paid cannot be negative."

        # Consistency between payment status and amount paid
        if self.payment_status == 'paid' and self.amount_paid != self.total_price:
            errors['amount_paid'] = "Amount paid must equal total price when payment status is 'Paid'."
        if self.payment_status == 'deposit_paid':
            if self.deposit_amount is None or self.deposit_amount <= 0:
                errors['deposit_amount'] = "Deposit amount must be set when payment status is 'Deposit Paid'."
            if self.amount_paid != self.deposit_amount:
                errors['amount_paid'] = "Amount paid must equal the deposit amount when payment status is 'Deposit Paid'."
        if self.payment_status == 'unpaid' and self.amount_paid > 0:
            # Optionally add a check here if unpaid but amount paid > 0
            pass # Or raise an error depending on desired strictness

        # Booked rates non-negative
        if self.booked_daily_rate is not None and self.booked_daily_rate < 0:
            errors['booked_daily_rate'] = "Booked daily rate cannot be negative."
        if self.booked_weekly_rate is not None and self.booked_weekly_rate < 0:
            errors['booked_weekly_rate'] = "Booked weekly rate cannot be negative."
        if self.booked_monthly_rate is not None and self.booked_monthly_rate < 0:
            errors['booked_monthly_rate'] = "Booked monthly rate cannot be negative."
        if self.booked_package_price is not None and self.booked_package_price < 0:
            errors['booked_package_price'] = "Booked package price cannot be negative."


        # --- Relationship Consistency ---
        # Check package availability if a package is selected
        if self.package and not self.package.is_available:
            errors['package'] = f"The selected package '{self.package.name}' is currently not available."

        # Consistency between is_international_booking and driver residency
        if self.is_international_booking and self.driver_profile and self.driver_profile.is_australian_resident:
            errors['is_international_booking'] = "Cannot mark as international booking if the driver is an Australian resident."


        # --- Raise Errors ---
        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ['pickup_date', 'pickup_time', 'motorcycle']
        verbose_name = "Hire Booking"
        verbose_name_plural = "Hire Bookings"
