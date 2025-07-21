from django.db import models
import uuid
from payments.models import Payment


class ServiceBooking(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("online_full", "Full Payment Online"),
        ("online_deposit", "Deposit Payment Online"),
        ("in_store_full", "Full Payment Store"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("deposit_paid", "Deposit Paid"),
        ("paid", "Fully Paid"),
        ("refunded", "Refunded"),
    ]
    BOOKING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("declined", "Declined by Admin"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
        ("DECLINED_REFUNDED", "Declined and Refunded"),
    ]

    service_booking_reference = models.CharField(
        max_length=20, unique=True, blank=True, null=True
    )
    service_type = models.ForeignKey(
        "service.ServiceType",
        on_delete=models.PROTECT,
        related_name="service_bookings",
        help_text="Selected service type.",
    )
    service_profile = models.ForeignKey(
        "service.ServiceProfile",
        on_delete=models.CASCADE,
        related_name="service_bookings",
        help_text="The customer profile associated with this temporary booking.",
    )
    customer_motorcycle = models.ForeignKey(
        "service.CustomerMotorcycle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_bookings",
        help_text="Chosen motorcycle for this service (set in a later step).",
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        related_name="related_service_booking_payment",
        null=True,
        blank=True,
        help_text="Link to the associated payment record.",
    )
    calculated_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    calculated_deposit_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="Method by which the payment was made.",
    )

    currency = models.CharField(
        max_length=3,
        default="AUD",
        help_text="The three-letter ISO currency code for the booking.",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent associated with this booking.",
    )

    service_date = models.DateField(help_text="Requested date for the service.")
    dropoff_date = models.DateField(help_text="Requested date for the drop off.")
    dropoff_time = models.TimeField(
        help_text="Requested drop-off time for the service.",
        null=True,
        blank=True,
    )
    estimated_pickup_date = models.DateField(
        blank=True, null=True, help_text="Estimated pickup date set by admin."
    )
    estimated_pickup_time = models.TimeField(
        blank=True, null=True, help_text="Estimated pickup time set by admin."
    )

    after_hours_drop_off = models.BooleanField(
        default=False,
        help_text="Indicates if the customer chose the after-hours drop-off option.",
    )

    booking_status = models.CharField(
        max_length=30, choices=BOOKING_STATUS_CHOICES, default="PENDING_CONFIRMATION"
    )
    customer_notes = models.TextField(
        blank=True, null=True, help_text="Any additional notes from the customer."
    )

    service_terms_version = models.ForeignKey(
        "service.ServiceTerms",
        on_delete=models.PROTECT,
        related_name="service_bookings",
        null=True,
        blank=True,
        help_text="The specific version of the Service T&Cs the user agreed to.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.service_booking_reference:
            self.service_booking_reference = f"SVC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.service_booking_reference} for {self.service_profile.name} on {self.dropoff_date}"

    class Meta:
        verbose_name = "Service Booking"
        verbose_name_plural = "Service Bookings"
        ordering = ["-created_at"]
