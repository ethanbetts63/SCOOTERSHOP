# hire/models/temp_booking_addon.py

from django.db import models
from django.core.exceptions import ValidationError
from .temp_hire_booking import TempHireBooking # Import TempHireBooking
from .hire_addon import AddOn # Import AddOn model
from dashboard.models import HireSettings # Import HireSettings for pricing strategy


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
        null=True, blank=True, # Store the price at time of booking
        help_text="Total price for this quantity of add-on at the time of selection." # Updated help text
    )

    def __str__(self):
        addon_name = self.addon.name if self.addon else 'Deleted Add-On'
        return f"{self.quantity} x {addon_name} for Temp Booking {str(self.temp_booking.session_uuid)[:8]}"

    def clean(self):
        """
        Custom validation for TempBookingAddOn data.
        Ensures quantity is within the allowed range for the associated AddOn,
        and that the booked_addon_price matches the calculated total price for the given quantity
        of the add-on for the temporary booking's duration.
        """
        super().clean()
        errors = {}

        # Import calculate_addon_price here to avoid circular import at module level
        from hire.hire_pricing import calculate_addon_price

        # Ensure quantity is within the allowed range for the associated AddOn
        if self.addon:
            if self.quantity is not None:
                if self.quantity < self.addon.min_quantity:
                    errors['quantity'] = f"Quantity for {self.addon.name} cannot be less than {self.addon.min_quantity}."
                if self.quantity > self.addon.max_quantity:
                    errors['quantity'] = f"Quantity for {self.addon.name} cannot be more than {self.addon.max_quantity}."
            else:
                # Quantity should always be set if addon is selected
                errors['quantity'] = "Quantity cannot be null if an add-on is selected."

            # Validate booked_addon_price against current addon price if addon is not null
            if self.booked_addon_price is not None:
                hire_settings = HireSettings.objects.first()

                if not hire_settings:
                    errors['booked_addon_price'] = "Hire settings are not configured, cannot validate add-on price."
                elif not (self.temp_booking and self.temp_booking.pickup_date and self.temp_booking.return_date and
                          self.temp_booking.pickup_time and self.temp_booking.return_time):
                    errors['booked_addon_price'] = "Temporary booking dates and times must be set to validate add-on price."
                else:
                    # Calculate the expected price for a single unit of this add-on for the temporary booking duration
                    expected_addon_price_per_unit = calculate_addon_price(
                        addon_instance=self.addon,
                        quantity=1, # Calculate for a single unit
                        pickup_date=self.temp_booking.pickup_date,
                        return_date=self.temp_booking.return_date,
                        pickup_time=self.temp_booking.pickup_time,
                        return_time=self.temp_booking.return_time,
                        hire_settings=hire_settings
                    )
                    # Calculate the expected total price for the given quantity
                    expected_total_addon_price = expected_addon_price_per_unit * self.quantity

                    # Compare the booked price with the calculated expected total price
                    if self.booked_addon_price != expected_total_addon_price:
                        errors['booked_addon_price'] = (
                            f"Booked add-on price ({self.booked_addon_price}) must match the calculated total price "
                            f"({expected_total_addon_price}) for {self.quantity} unit(s) of {self.addon.name}."
                        )

        if errors:
            raise ValidationError(errors)

    class Meta:
        unique_together = ('temp_booking', 'addon')
        verbose_name = "Temporary Booking Add-On"
        verbose_name_plural = "Temporary Booking Add-Ons"
