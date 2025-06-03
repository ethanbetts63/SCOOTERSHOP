from django.db import models
from django.core.exceptions import ValidationError
from service.models import ServiceProfile

class CustomerMotorcycle(models.Model):
    """
    Stores details of a customer's motorcycle for service bookings.
    """
    service_profile = models.ForeignKey(
        ServiceProfile,
        on_delete=models.CASCADE,
        related_name='customer_motorcycles',
        help_text="The customer profile this motorcycle belongs to."
    )

    brand = models.CharField(max_length=100, help_text="Brand of the motorcycle (e.g., Honda, Yamaha, or 'Other').")
    make = models.CharField(max_length=100, help_text="Specific make of the motorcycle (e.g., CBR600RR for Honda).")
    model = models.CharField(max_length=100, help_text="Model year or specific model identifier.")
    year = models.PositiveIntegerField(help_text="Manufacturing year of the motorcycle.")
    engine_size = models.CharField(max_length=50, blank=True, null=True, help_text="Engine displacement (e.g., 250cc, 1000cc).")
    rego = models.CharField(max_length=20, blank=True, null=True, help_text="Registration number (license plate).")
    vin_number = models.CharField(max_length=17, blank=True, null=True, unique=True, help_text="Vehicle Identification Number.") # VINs are typically 17 chars and unique.
    odometer = models.PositiveIntegerField(blank=True, null=True, help_text="Odometer reading in km or miles.")
    transmission_choices = [
        ('MANUAL', 'Manual'),
        ('AUTOMATIC', 'Automatic'),
        ('SEMI_AUTO', 'Semi-Automatic'),
    ]
    transmission = models.CharField(max_length=20, choices=transmission_choices, blank=True, null=True)
    engine_number = models.CharField(max_length=50, blank=True, null=True, help_text="Engine serial number.")
    image = models.ImageField(upload_to='motorcycle_images/', blank=True, null=True, help_text="Optional image of the motorcycle.")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year} {self.brand} {self.make} (Owner: {self.service_profile.name})"

    def clean(self):
        super().clean()
        if self.brand and self.brand.lower() == 'other' and not self.other_brand_name:
            raise ValidationError({'other_brand_name': "Please specify the brand name if 'Other' is selected."})
        if self.brand and self.brand.lower() != 'other' and self.other_brand_name:
            # Clear other_brand_name if a specific brand is chosen
            self.other_brand_name = None

    class Meta:
        verbose_name = "Customer Motorcycle"
        verbose_name_plural = "Customer Motorcycles"
        # A customer might have multiple motorcycles with the same make/model but different VIN/rego.
        # unique_together = (('service_profile', 'vin_number'),) # If VIN must be unique per profile.
