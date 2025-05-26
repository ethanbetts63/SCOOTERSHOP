# hire/models/temp_hire_booking.py

import uuid
from django.db import models
from django.utils import timezone
from inventory.models import Motorcycle
from .driver_profile import DriverProfile
from .hire_addon import AddOn
from .hire_packages import Package


class TempHireBooking(models.Model):
    """
    Temporarily stores booking details as the user progresses through the steps.
    Data is copied to HireBooking upon successful completion.
    """
    # Link to the session using a UUID for security and uniqueness
    session_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    # Optional: Link to a registered user if they are logged in
    # from django.conf import settings
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # --- Booking Details collected across steps ---
    # Step 1: Dates, Times, License
    pickup_date = models.DateField(null=True, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    return_time = models.TimeField(null=True, blank=True)
    has_motorcycle_license = models.BooleanField(default=False) # Store license status here

    # Step 2: Selected Motorcycle
    motorcycle = models.ForeignKey(
        Motorcycle,
        on_delete=models.SET_NULL, # Use SET_NULL in case the motorcycle is deleted
        related_name='temp_hire_bookings',
        null=True, blank=True
    )

    # Step 3: Add-ons and Package
    # Add-ons handled via TempBookingAddOn intermediate model below
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL, # Use SET_NULL
        related_name='temp_hire_bookings',
        null=True, blank=True
    )
    # Store booked price of package at the time of selection
    total_package_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    # Step 4: Driver Details
    driver_profile = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL, # Use SET_NULL
        related_name='temp_hire_bookings',
        null=True, blank=True
    )
    # Need a way to track if this is an international booking based on driver profile
    is_international_booking = models.BooleanField(default=False)

    # Step 5: Payment Option (NEW FIELD)
    PAYMENT_OPTIONS = [
        ('online_full', 'Online (Full Payment)'),
        ('online_deposit', 'Online (Deposit Only)'),
        ('in_store', 'Pay In Store'),
    ]
    payment_option = models.CharField(
        max_length=20,
        choices=PAYMENT_OPTIONS,
        null=True,
        blank=True,
        help_text="The selected payment option for this booking."
    )

    # --- Calculated / Booked Prices ---
    # Store the rates and total price at the time the bike is selected/confirmed
    booked_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    total_hire_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, # Price might not be calculated until step 2 or later
        help_text="Calculated total price for the motorcycle hire duration only."
    )
    total_addons_price = models.DecimalField(
         max_digits=10, decimal_places=2,
         default=0,
         help_text="Calculated total price for selected add-ons."
    )
    grand_total = models.DecimalField(
         max_digits=10, decimal_places=2,
         null=True, blank=True, # Calculated later
         help_text="Sum of total_hire_price, total_addons_price, and total_package_price."
    )
    # Add deposit_amount field for online_deposit option
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="The deposit amount required for the booking."
    )
    # Add currency field to TempHireBooking model
    currency = models.CharField(
        max_length=3,
        default='AUD', 
        help_text="The three-letter ISO currency code for the booking."
    )


    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        motorcycle_str = self.motorcycle.model if self.motorcycle else 'No bike selected'
        date_range = f"({self.pickup_date} to {self.return_date})" if self.pickup_date and self.return_date else "(Dates not set)"
        return f"Temp Booking ({str(self.session_uuid)[:8]}): {motorcycle_str} {date_range}"

    # You can add clean methods here for cross-field validation if needed,
    # similar to HireBooking, but form validation might be sufficient during the process.

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Temporary Hire Booking"
        verbose_name_plural = "Temporary Hire Bookings"

