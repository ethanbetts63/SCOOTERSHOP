from django.db import models # Django models
from django.core.exceptions import ValidationError # Validation errors
from .hire_booking import HireBooking # Import HireBooking model
from .hire_addon import AddOn # Import AddOn model


class BookingAddOn(models.Model):
    """
    An intermediate model linking HireBooking and AddOn, allowing for quantity.
    """
    booking = models.ForeignKey(
        HireBooking,
        on_delete=models.CASCADE,
        related_name='booking_addons'
    )
    addon = models.ForeignKey(
        AddOn,
        on_delete=models.CASCADE,
        related_name='addon_bookings'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="The quantity of this add-on included in the booking."
    )

    # Price of one unit at the time of booking
    booked_addon_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Price of one unit of this add-on at the time of booking."
    )

    def __str__(self):
        return f"{self.quantity} x {self.addon.name} for Booking {self.booking.booking_reference}"

    def clean(self):
        """
        Custom validation for BookingAddOn data.
        """
        super().clean()

        # Ensure the selected add-on is available
        if self.addon and not self.addon.is_available:
             raise ValidationError({'addon': f"The add-on '{self.addon.name}' is currently not available."})

        if self.addon: 
            if self.booked_addon_price != self.addon.cost:
                 raise ValidationError({'booked_addon_price': f"Booked add-on price must match the current price of the add-on ({self.addon.cost})."})


    class Meta:
        # Ensure you can't add the same add-on to the same booking multiple times
        unique_together = ('booking', 'addon')