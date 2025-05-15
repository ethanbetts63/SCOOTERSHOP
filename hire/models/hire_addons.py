#models/booking_addons.py

from django.db import models
from .hire_booking import HireBooking
from .hire_addons import AddOn

class BookingAddOn(models.Model):
    """
    An intermediate model linking HireBooking and AddOn, allowing for quantity.
    """
    booking = models.ForeignKey(
        HireBooking,
        on_delete=models.CASCADE,
        related_name='booking_addons' # Renamed to 'booking_addons' for clarity
    )
    addon = models.ForeignKey(
        AddOn,
        on_delete=models.CASCADE,
        related_name='addon_bookings' # Renamed to 'addon_bookings' for clarity
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="The quantity of this add-on included in the booking."
    )
    
    booked_addon_price = models.DecimalField(
    max_digits=8,
    decimal_places=2,
    help_text="Price of one unit of this add-on at the time of booking."
)

    def __str__(self):
        return f"{self.quantity} x {self.addon.name} for Booking {self.booking.booking_reference}"

    class Meta:
        # Ensures you can't add the same add-on to the same booking multiple times without changing quantity
        unique_together = ('booking', 'addon')