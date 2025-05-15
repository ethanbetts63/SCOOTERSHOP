from django.db import models
# Import the AddOn model
from .hire_addon import AddOn

class Package(models.Model):
    """
    Represents a bundle of add-ons offered as a package.
    """
    name = models.CharField(max_length=100, help_text="Name of the package.")
    description = models.TextField(blank=True, null=True, help_text="Description of the package.")

    # Many-to-Many relationship with AddOn
    # A package can have multiple add-ons, and an add-on can be in multiple packages.
    add_ons = models.ManyToManyField(
        AddOn,
        related_name='packages',
        blank=True,
        help_text="Select the individual add-ons included in this package."
    )

    # In Package model 
    package_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The current price of this package bundle."
    )

    # --- Availability/Visibility 
    is_available = models.BooleanField(default=True, help_text="Is this package currently available for booking?")

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Hire Package"
        verbose_name_plural = "Hire Packages"