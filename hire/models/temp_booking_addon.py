# hire/models/temp_booking_addon.py

from django.db import models
from django.core.exceptions import ValidationError
from .temp_hire_booking import TempHireBooking # Import TempHireBooking
from .hire_addon import AddOn # Import AddOn model


class TempBookingAddOn(models.Model):
    """
    An intermediate model linking TempHireBooking and AddOn, allowing for quantity.
    This mirrors BookingAddOn for temporary bookings.
    """
    temp_booking = models.ForeignKey(
        TempHireBooking,
        on_delete=models.CASCADE, # If temp booking is deleted, delete these too
        related_name='temp_booking_addons'
    )
    addon = models.ForeignKey(
        AddOn,
        on_delete=models.SET_NULL, # Use SET_NULL in case addon is deleted
        related_name='temp_addon_bookings',
        null=True, blank=True # Allow null if addon is deleted
    )
    quantity = models.PositiveIntegerField(default=1)

    # Price of one unit at the time of selection
    booked_addon_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True, blank=True # Store the price at time of booking
    )

    def __str__(self):
        addon_name = self.addon.name if self.addon else 'Deleted Add-On'
        return f"{self.quantity} x {addon_name} for Temp Booking {str(self.temp_booking.session_uuid)[:8]}"

    def clean(self):
        """
        Custom validation for TempBookingAddOn data.
        """
        super().clean()
        errors = {}

        # Ensure quantity is within the allowed range for the associated AddOn
        if self.addon:
            if self.quantity is not None:
                if self.quantity < self.addon.min_quantity:
                    errors['quantity'] = f"Quantity for {self.addon.name} cannot be less than {self.addon.min_quantity}."
                if self.quantity > self.addon.max_quantity:
                    errors['quantity'] = f"Quantity for {self.addon.name} cannot be more than {self.addon.max_quantity}."
            else:
                errors['quantity'] = "Quantity cannot be null." # Quantity should always be set if addon is selected

            # Validate booked_addon_price against current addon price if addon is not null
            if self.booked_addon_price is not None and self.addon and self.booked_addon_price != self.addon.cost:
                errors['booked_addon_price'] = f"Booked add-on price must match the current price of the add-on ({self.addon.cost})."

        if errors:
            raise ValidationError(errors)

    class Meta:
        # Ensure you can't add the same add-on to the same temp booking multiple times
        unique_together = ('temp_booking', 'addon')
        verbose_name = "Temporary Booking Add-On"
        verbose_name_plural = "Temporary Booking Add-Ons"
