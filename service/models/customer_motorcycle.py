from django.db import models
from datetime import date
from django.core.exceptions import ValidationError


class CustomerMotorcycle(models.Model):
    service_profile = models.ForeignKey(
        "service.ServiceProfile",
        on_delete=models.CASCADE,
        related_name="customer_motorcycles",
        help_text="The customer profile this motorcycle belongs to.",
        null=True,
        blank=True,
    )

    brand = models.CharField(
        max_length=100,
        help_text="Brand of the motorcycle (e.g., Honda, Yamaha, or 'Other').",
    )
    model = models.CharField(
        max_length=100, help_text="Model year or specific model identifier."
    )
    year = models.PositiveIntegerField(
        help_text="Manufacturing year of the motorcycle."
    )
    rego = models.CharField(
        max_length=20, help_text="Registration number (license plate)."
    )
    odometer = models.PositiveIntegerField(help_text="Odometer reading in km.")
    transmission_choices = [
        ("MANUAL", "Manual"),
        ("AUTOMATIC", "Automatic"),
        ("SEMI_AUTO", "Semi-Automatic"),
    ]
    transmission = models.CharField(max_length=20, choices=transmission_choices)
    engine_size = models.CharField(
        max_length=50, help_text="Engine displacement (e.g., 250cc, 1000cc)."
    )
    vin_number = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        unique=True,
        help_text="(optional) Vehicle Identification Number.",
    )
    engine_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="(optional) Engine serial number.",
    )
    image = models.ImageField(
        upload_to="motorcycle_images/",
        blank=True,
        null=True,
        help_text="(optional) Image of the motorcycle.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year} {self.brand} {self.model}"

    def clean(self):
        super().clean()

        if not self.brand:
            raise ValidationError({"brand": "Motorcycle brand is required."})
        if not self.model:
            raise ValidationError({"model": "Motorcycle model is required."})
        if not self.year:
            raise ValidationError({"year": "Motorcycle year is required."})
        if not self.rego:
            raise ValidationError({"rego": "Motorcycle registration is required."})

        if self.odometer is None:
            raise ValidationError({"odometer": "Motorcycle odometer is required."})
        if not self.transmission:
            raise ValidationError(
                {"transmission": "Motorcycle transmission type is required."}
            )
        if not self.engine_size:
            raise ValidationError(
                {"engine_size": "Motorcycle engine size is required."}
            )

        current_year = date.today().year
        if self.year and self.year > current_year:
            raise ValidationError({"year": "Motorcycle year cannot be in the future."})
        if self.year and self.year < current_year - 100:
            raise ValidationError(
                {"year": "Motorcycle year seems too old. Please check the year."}
            )

        if self.vin_number and len(self.vin_number) != 17:
            raise ValidationError(
                {"vin_number": "VIN number must be 17 characters long."}
            )

        if self.odometer is not None and self.odometer < 0:
            raise ValidationError({"odometer": "Odometer reading cannot be negative."})

    class Meta:
        verbose_name = "Customer Motorcycle"
        verbose_name_plural = "Customer Motorcycles"
