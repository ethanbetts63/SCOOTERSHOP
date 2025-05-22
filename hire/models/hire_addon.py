from django.db import models # Django models
from django.core.exceptions import ValidationError # Validation errors

class AddOn(models.Model):
    """
    Represents an individual add-on item available for hire.
    """
    name = models.CharField(max_length=100, help_text="Name of the add-on.")
    description = models.TextField(blank=True, null=True, help_text="Description of the add-on.")

    # Pricing
    cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Cost of the add-on per item per day."
    )

    # Quantity controls (NEW FIELDS)
    min_quantity = models.PositiveIntegerField(
        default=1,
        help_text="Minimum quantity allowed for this add-on."
    )
    max_quantity = models.PositiveIntegerField(
        default=1,
        help_text="Maximum quantity allowed for this add-on."
    )

    # Availability
    is_available = models.BooleanField(default=True, help_text="Is this add-on currently available for booking?")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        """
        Custom validation for AddOn data.
        """
        super().clean()
        errors = {}
        if self.cost < 0:
            errors['cost'] = "Add-on cost cannot be negative."
        
        # Validate min_quantity and max_quantity
        if self.min_quantity < 1:
            errors['min_quantity'] = "Minimum quantity must be at least 1."
        if self.max_quantity < self.min_quantity:
            errors['max_quantity'] = "Maximum quantity cannot be less than minimum quantity."
        
        if errors:
            raise ValidationError(errors)


    class Meta:
        ordering = ['name']
        verbose_name = "Hire Add-On"
        verbose_name_plural = "Hire Add-Ons"
