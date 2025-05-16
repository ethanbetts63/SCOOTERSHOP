# SCOOTER_SHOP/inventory/models.py

from django.db import models
from django.urls import reverse
# Need to import the User model from the users app
from users.models import User


# Model for motorcycle conditions
class MotorcycleCondition(models.Model):
    name = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=50)

    def __str__(self):
        return self.display_name

# Main motorcycle model representing inventory
class Motorcycle(models.Model):
    STATUS_CHOICES = [
        ('for_sale', 'For Sale'),
        ('sold', 'Sold'),
        ('for_hire', 'For Hire'),
        ('unavailable', 'Unavailable'),
    ]

    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('demo', 'Demo'),
        ('hire', 'Hire'),
    ]

    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('semi-auto', 'Semi-Automatic'),
    ]

    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    # Made price nullable and blankable
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Sale price (if applicable)")

    # Additional identification fields
    vin_number = models.CharField(max_length=50, blank=True, null=True, help_text="Vehicle Identification Number")
    engine_number = models.CharField(max_length=50, blank=True, null=True, help_text="Engine number/identifier")
    # Use the User model from the users app
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="owned_motorcycles", null=True, blank=True)

    # Keep the original field for backwards compatibility / simple cases
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)

    # Field for multiple conditions (like 'Used', 'Hire')
    conditions = models.ManyToManyField(
        MotorcycleCondition,
        related_name='motorcycles',
        blank=True,
        help_text="Select all applicable conditions (e.g., Used, Hire)",
    )

    odometer = models.IntegerField(null=True, blank=True) # Odometer is not made required based on your list
    engine_size = models.CharField(max_length=50)

    # Made seats nullable and blankable
    seats = models.IntegerField(
        help_text="Number of seats on the motorcycle",
        null=True, blank=True
    )

    # Made transmission nullable and blankable
    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        help_text="Motorcycle transmission type",
        null=True, blank=True
    )

    # Made description nullable and blankable
    description = models.TextField(null=True, blank=True)
    image = models.FileField(upload_to='motorcycles/', null=True, blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    is_available = models.BooleanField(default=True, help_text="Is this bike generally available for sale or in the active hire fleet?")
    rego = models.CharField(max_length=20, help_text="Registration number", null=True, blank=True)
    rego_exp = models.DateField(help_text="Registration expiration date", null=True, blank=True)
    stock_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    # Hire rates made nullable and blankable
    daily_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per day for hiring (if applicable)"
    )

    # New hire rate fields made nullable and blankable
    weekly_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per week for hiring (if applicable)"
    )

    monthly_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per month for hiring (if applicable)"
    )

    hourly_hire_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per hour for hiring (if applicable)"
    )


    # Returns a string representation of the motorcycle
    def __str__(self):
        return f"{self.year} {self.brand} {self.model}"

    # Provides the URL to access this specific motorcycle
    # Remember to update the URL name to 'inventory:motorcycle-detail'
    # in your templates and code after namespacing URLs
    def get_absolute_url(self):
        return reverse('inventory:motorcycle-detail', kwargs={'pk': self.pk})

    # Returns formatted string of all conditions
    def get_conditions_display(self):
        """Return a formatted string of all conditions"""
        if self.conditions.exists():
            return ", ".join([condition.display_name for condition in self.conditions.all()])
        elif self.condition:
             # Fall back to the old field if no conditions are set in the new field
            return dict(self.CONDITION_CHOICES).get(self.condition, self.condition).title()
        return "N/A" # Or some default if neither is set

    # Checks if the motorcycle is available for hire
    def is_for_hire(self):
        """Checks if 'Hire' is one of the conditions."""
        return self.conditions.filter(name='hire').exists()

# Model for storing additional motorcycle images
class MotorcycleImage(models.Model):
    motorcycle = models.ForeignKey(Motorcycle, on_delete=models.CASCADE, related_name='images')
    image = models.FileField(upload_to='motorcycles/additional/')

    def __str__(self):
        return f"Image for {self.motorcycle}"