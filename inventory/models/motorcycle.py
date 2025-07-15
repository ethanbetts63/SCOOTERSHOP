from django.db import models
from django.urls import reverse


class Motorcycle(models.Model):
    STATUS_CHOICES = [
        ("for_sale", "For Sale"),
        ("sold", "Sold"),
        ("reserved", "Reserved"),
        ("unavailable", "Unavailable"),
    ]

    CONDITION_CHOICES = [
        ("new", "New"),
        ("used", "Used"),
        ("demo", "Demo"),
    ]

    TRANSMISSION_CHOICES = [
        ("automatic", "Automatic"),
        ("manual", "Manual"),
        ("semi-auto", "Semi-Automatic"),
    ]

    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sale price (if applicable)",
    )

    quantity = models.IntegerField(
        default=1,
        help_text="Quantity of this motorcycle model in stock. Leave blank for unique used bikes.",
    )

    vin_number = models.CharField(
        max_length=50, blank=True, null=True, help_text="Vehicle Identification Number"
    )
    engine_number = models.CharField(
        max_length=50, blank=True, null=True, help_text="Engine number/identifier"
    )

    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)

    conditions = models.ManyToManyField(
        "inventory.MotorcycleCondition",
        related_name="motorcycles",
        blank=True,
        help_text="Select all applicable conditions (e.g., Used, New, Demo.)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="for_sale",
        help_text="The sales status of the motorcycle.",
    )
    odometer = models.IntegerField(default=0)
    engine_size = models.IntegerField(help_text="Engine size in cubic centimeters (cc)")

    seats = models.IntegerField(
        help_text="Number of seats on the motorcycle", null=True, blank=True
    )

    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        help_text="Motorcycle transmission type",
        null=True,
        blank=True,
    )

    description = models.TextField(null=True, blank=True)
    image = models.FileField(upload_to="motorcycles/", null=True, blank=True)
    youtube_link = models.URLField(max_length=255, blank=True, null=True, help_text="An optional link to a YouTube video for this motorcycle.")
    date_posted = models.DateTimeField(auto_now_add=True)
    is_available = models.BooleanField(
        default=True, help_text="Is this bike generally available for sale?"
    )
    rego = models.CharField(
        max_length=20, help_text="Registration number", null=True, blank=True
    )
    rego_exp = models.DateField(
        help_text="Registration expiration date", null=True, blank=True
    )
    stock_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.year} {self.brand} {self.model}"

    def get_absolute_url(self):
        return reverse("inventory:motorcycle-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if self.status == "for_sale":
            self.is_available = True
        else:
            self.is_available = False
        super().save(*args, **kwargs)

    def get_conditions_display(self):
        if self.conditions.exists():
            return ", ".join(
                [condition.display_name for condition in self.conditions.all()]
            )
        elif self.condition:
            return (
                dict(self.CONDITION_CHOICES).get(self.condition, self.condition).title()
            )
        return "N/A"
