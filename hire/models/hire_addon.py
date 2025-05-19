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
        if self.cost < 0:
            raise ValidationError({'cost': "Add-on cost cannot be negative."})


    class Meta:
        ordering = ['name']
        verbose_name = "Hire Add-On"
        verbose_name_plural = "Hire Add-Ons"