from django.db import models
from users.models import User
from inventory.models import Motorcycle
import uuid
# from models.hire_packages import Package
# from models.hire_addons import Addons

# Choices for booking status
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('cancelled', 'Cancelled'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('no_show', 'No Show'),
]

# Choices for payment status (from your initial model)
PAYMENT_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('deposit_paid', 'Deposit Paid'),
    ('paid', 'Fully Paid'),
    ('refunded', 'Refunded'),
]

# Choices for payment method (from previous discussion)
PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('card', 'Card'),
    ('online', 'Online'),
    ('at_desk', 'At Desk (Pending Payment)'), # Added option for your flow
    ('other', 'Other')
]


# Model for motorcycle hire bookings
class HireBooking(models.Model):
    # --- Relationships ---
    # Link to the Motorcycle instance being hired.
    motorcycle = models.ForeignKey(
        Motorcycle, # Link to the Motorcycle model
        on_delete=models.CASCADE,
        related_name='hire_bookings',
        limit_choices_to={'conditions__name': 'hire'} # Keep this filter if you need it
    )

    # Link to the customer making the booking.
    # Customer details like name, address, etc., are stored on the User model.
    customer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='hire_bookings',
        null=True, # Allow booking without a registered user initially (e.g., walk-in)
        blank=True
    )

    # Link to the selected package (Optional).
    package = models.ForeignKey(
        'Package', # Use string literal if Package is defined later in the same file
        on_delete=models.SET_NULL,
        related_name='hire_bookings',
        null=True,
        blank=True
    )

    # Link to individually selected add-ons (Optional).
    # If you need quantity per add-on (e.g., 2 helmets), you'll need a 'through' model here.
    add_ons = models.ManyToManyField(
        'AddOn', # Use string literal if AddOn is defined later in the same file
        related_name='hire_bookings',
        blank=True # Allow bookings with no add-ons
    )

    # --- Booking Dates and Times ---
    # Pickup date of the hire.
    pickup_date = models.DateField(help_text="Pickup date")
    # Pickup time of the hire.
    pickup_time = models.TimeField(help_text="Pickup time")

    # Return date of the hire.
    return_date = models.DateField(help_text="Return date")
    # Return time of the hire.
    return_time = models.TimeField(help_text="Return time")

    # --- Booking Identifiers and Flags ---
    # Unique reference code for the booking.
    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    # Flag if the booking requires international documentation (e.g., IDP).
    is_international_booking = models.BooleanField(default=False, help_text="Indicates if the booking requires international documentation/considerations.")

    # --- Financial Details (from initial model draft) ---
    # Daily rate applied at the time of booking.
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # Weekly rate applied at the time of booking.
    booked_weekly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # Monthly rate applied at the time of booking.
    booked_monthly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # Total calculated price for the entire hire booking.
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Required deposit amount for the booking.
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # Amount currently paid towards the booking.
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Current payment status of the booking.
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    # Method used for payment.
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, help_text="Method by which the payment was made.")


    # --- Status and Notes ---
    # Current status of the booking lifecycle.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Notes provided by the customer during booking.
    customer_notes = models.TextField(blank=True, null=True)
    # Internal notes added by staff.
    internal_notes = models.TextField(blank=True, null=True)

    # --- Timestamps ---
    # Timestamp when the booking was created.
    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the booking was last updated.
    updated_at = models.DateTimeField(auto_now=True)

    # --- Methods ---
    # Saves the booking instance.
    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    # String representation of the booking.
    def __str__(self):
        return f"Hire: {self.motorcycle} ({self.pickup_date} to {self.return_date}) - {self.status}"

    # --- Meta Class ---
    class Meta:
        # Default ordering for listings.
        ordering = ['pickup_date', 'pickup_time', 'motorcycle']
        # Verbose name for the model in the admin.
        verbose_name = "Hire Booking"
        verbose_name_plural = "Hire Bookings"