from django.db import models

PRICE_TYPE_CHOICES = [
    ('fixed', 'Fixed Price (per booking)'),
    ('per_day', 'Price Per Day'),
    ('per_booking', 'Price Per Booking'), # Redundant with 'fixed', maybe refine
    ('per_item', 'Price Per Item (if quantity tracked via through model)'),
]

class AddOn(models.Model):
    """
    Represents an individual hire add-on (e.g., helmet, GPS, insurance).
    """
    name = models.CharField(max_length=100, help_text="Name of the add-on.")
    description = models.TextField(blank=True, null=True, help_text="Description of the add-on.")

    # --- Pricing ---
    price_type = models.CharField(
        max_length=20,
        choices=PRICE_TYPE_CHOICES,
        default='fixed',
        help_text="How the add-on price is calculated."
    )
    cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="The cost of the add-on based on the price type."
    )

    # --- Availability/Visibility (Optional additions) ---
    is_available = models.BooleanField(default=True, help_text="Is this add-on currently available for booking?")
    # image = models.ImageField(upload_to='hire_addons/', blank=True, null=True, help_text="Image for the add-on.")

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Hire Add-On"
        verbose_name_plural = "Hire Add-Ons"