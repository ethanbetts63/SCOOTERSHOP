from django.db import models
import uuid


class TempServiceBooking(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("online_full", "Full Payment Online"),
        ("online_deposit", "Deposit Payment Online"),
        ("in_store_full", "Full Payment Store"),
    ]

    session_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique identifier for retrieving the temporary booking.",
    )
    service_type = models.ForeignKey(
        "service.ServiceType",
        on_delete=models.PROTECT,
        related_name="temp_service_bookings",
        help_text="Selected service type.",
    )
    service_profile = models.ForeignKey(
        "service.ServiceProfile",
        on_delete=models.CASCADE,
        related_name="temp_service_bookings",
        null=True,
        blank=True,
        help_text="The customer profile associated with this temporary booking.",
    )
    customer_motorcycle = models.ForeignKey(
        "service.CustomerMotorcycle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="temp_service_bookings",
        help_text="Chosen motorcycle for this service (set in a later step).",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="The selected payment option for this booking.",
    )
    service_terms_version = models.ForeignKey(
        "service.ServiceTerms",
        on_delete=models.PROTECT,
        related_name="temp_service_bookings",
        null=True,
        blank=True,
        help_text="The specific version of the Service T&Cs the user agreed to.",
    )

    service_date = models.DateField(help_text="Requested date for the service.")
    dropoff_date = models.DateField(
        null=True, blank=True, help_text="Requested date for the drop off."
    )
    dropoff_time = models.TimeField(
        null=True, blank=True, help_text="Requested drop-off time for the service."
    )
    estimated_pickup_date = models.DateField(
        null=True, blank=True, help_text="Estimated pickup date set by admin."
    )

    after_hours_drop_off = models.BooleanField(
        default=False, help_text="Stores the user's choice for after-hours drop-off."
    )

    customer_notes = models.TextField(
        blank=True, null=True, help_text="Any additional notes from the customer."
    )
    calculated_deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated deposit amount, if applicable.",
    )
    calculated_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        profile_name = (
            self.service_profile.name if self.service_profile else "Anonymous"
        )
        return f"Temp Booking {self.session_uuid}  for {profile_name} on {self.dropoff_date}"

    class Meta:
        verbose_name = "Temporary Service Booking"
        verbose_name_plural = "Temporary Service Bookings"
        ordering = ["-created_at"]
