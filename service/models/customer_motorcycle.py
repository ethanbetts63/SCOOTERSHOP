from django.db import models
from datetime import date
from django.core.exceptions import ValidationError

class CustomerMotorcycle(models.Model):
    """
    Stores details of a customer's motorcycle for service bookings.
    """
    service_profile = models.ForeignKey(
        'service.ServiceProfile',
        on_delete=models.CASCADE,
        related_name='customer_motorcycles',
        help_text="The customer profile this motorcycle belongs to.",
        null=True,
        blank=True
    )

    brand = models.CharField(max_length=100, help_text="Brand of the motorcycle (e.g., Honda, Yamaha, or 'Other').")
    # Removed 'make' field as it's now redundant
    model = models.CharField(max_length=100, help_text="Model year or specific model identifier.")
    year = models.PositiveIntegerField(help_text="Manufacturing year of the motorcycle.")
    rego = models.CharField(max_length=20, help_text="Registration number (license plate).")
    odometer = models.PositiveIntegerField(help_text="Odometer reading in km.")
    transmission_choices = [
        ('MANUAL', 'Manual'),
        ('AUTOMATIC', 'Automatic'),
        ('SEMI_AUTO', 'Semi-Automatic'),
    ]
    transmission = models.CharField(max_length=20, choices=transmission_choices)
    engine_size = models.CharField(max_length=50, help_text="Engine displacement (e.g., 250cc, 1000cc).") # Removed blank=True, null=True
    vin_number = models.CharField(max_length=17, blank=True, null=True, unique=True, help_text="(optional) Vehicle Identification Number.")
    engine_number = models.CharField(max_length=50, blank=True, null=True, help_text="(optional) Engine serial number.")
    image = models.ImageField(upload_to='motorcycle_images/', blank=True, null=True, help_text="(optional) Image of the motorcycle.")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner_info = self.service_profile.name if self.service_profile else "N/A"
        # Updated string representation since 'make' is removed
        return f"{self.year} {self.brand} {self.model} (Owner: {owner_info})"

    def clean(self):
        super().clean()

        # Rule 1: Ensure required fields are not empty
        if not self.brand:
            raise ValidationError({'brand': "Motorcycle brand is required."})
        if not self.model:
            raise ValidationError({'model': "Motorcycle model is required."})
        if not self.year:
            raise ValidationError({'year': "Motorcycle year is required."})
        if not self.rego:
            raise ValidationError({'rego': "Motorcycle registration is required."})
        if not self.odometer:
            raise ValidationError({'odometer': "Motorcycle odometer is required."}) # Corrected key
        if not self.transmission:
            raise ValidationError({'transmission': "Motorcycle transmission type is required."})
        if not self.engine_size:
            raise ValidationError({'engine_size': "Motorcycle engine size is required."})
        

        # Rule 2: Validate motorcycle year
        current_year = date.today().year
        if self.year and self.year > current_year:
            raise ValidationError({'year': "Motorcycle year cannot be in the future."})
        if self.year and self.year < current_year - 100: 
            raise ValidationError({'year': "Motorcycle year seems too old. Please check the year."})

        # Rule 3: Validate VIN number length if provided
        if self.vin_number and len(self.vin_number) != 17:
            raise ValidationError({'vin_number': "VIN number must be 17 characters long."})
        
        # Rule 4: Ensure odometer reading is not negative if provided
        if self.odometer is not None and self.odometer < 0:
            raise ValidationError({'odometer': "Odometer reading cannot be negative."})

    class Meta:
        verbose_name = "Customer Motorcycle"
        verbose_name_plural = "Customer Motorcycles"

