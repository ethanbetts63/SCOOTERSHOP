from django.db import models # Django models
from django.core.exceptions import ValidationError # Validation errors
from .hire_booking import HireBooking # Import HireBooking model
from .hire_addon import AddOn # Import AddOn model
from dashboard.models import HireSettings # Import HireSettings for pricing strategy


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
        help_text="Total price for this quantity of add-on at the time of booking." # Updated help text
    )

    def __str__(self):
        return f"{self.quantity} x {self.addon.name} for Booking {self.booking.booking_reference}"

    def clean(self):
        """
        Custom validation for BookingAddOn data.
        Ensures the selected add-on is available, and that the booked_addon_price
        matches the calculated total price for the given quantity of the add-on
        at the time of booking.
        """
        super().clean()
        errors = {}

        # Import calculate_addon_price here to avoid circular import at module level
        from hire.views.hire_pricing import calculate_addon_price

        # Ensure the selected add-on is available
        if self.addon and not self.addon.is_available:
             errors['addon'] = f"The add-on '{self.addon.name}' is currently not available."

        # Validate quantity against add-on's min/max quantity
        if self.addon and self.quantity is not None:
            if self.quantity < self.addon.min_quantity:
                errors['quantity'] = f"Quantity for {self.addon.name} cannot be less than {self.addon.min_quantity}."
            if self.quantity > self.addon.max_quantity:
                errors['quantity'] = f"Quantity for {self.addon.name} cannot be more than {self.addon.max_quantity}."
        elif self.addon and self.quantity is None:
            errors['quantity'] = "Quantity cannot be null if an add-on is selected."

        # Validate booked_addon_price against the dynamically calculated price
        if self.addon and self.booked_addon_price is not None:
            hire_settings = HireSettings.objects.first()
            
            if not hire_settings:
                errors['booked_addon_price'] = "Hire settings are not configured, cannot validate add-on price."
            elif not (self.booking and self.booking.pickup_date and self.booking.return_date and
                      self.booking.pickup_time and self.booking.return_time):
                errors['booked_addon_price'] = "Booking dates and times must be set to validate add-on price."
            else:
                # Calculate the expected price for a single unit of this add-on for the booking duration
                expected_addon_price_per_unit = calculate_addon_price(
                    addon_instance=self.addon,
                    quantity=1, # Calculate for a single unit
                    pickup_date=self.booking.pickup_date,
                    return_date=self.booking.return_date,
                    pickup_time=self.booking.pickup_time,
                    return_time=self.booking.return_time,
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
        unique_together = ('booking', 'addon')
