from django.db import models
import uuid
from decimal import Decimal

PAYMENT_STATUS_CHOICES = [
    ("unpaid", "Unpaid"),
    ("deposit_paid", "Deposit Paid"),
    ("refunded", "Refunded"),
]
BOOKING_STATUS_CHOICES = [
    ("pending_confirmation", "Pending Confirmation"),
    ("confirmed", "Confirmed"),
    ("cancelled", "Cancelled"),
    ("declined", "Declined by Admin"),
    ("completed", "Completed"),
    ("no_show", "No Show"),
    ("declined_refunded", "Declined and Refunded"),
    ("enquired", "Enquired"),
]


class SalesBooking(models.Model):
    motorcycle = models.ForeignKey(
        "inventory.Motorcycle",
        on_delete=models.PROTECT,
        related_name="sales_bookings",
        help_text="The motorcycle associated with this sales booking.",
    )
    sales_profile = models.ForeignKey(
        "inventory.SalesProfile",
        on_delete=models.PROTECT,
        related_name="sales_bookings",
        help_text="The customer's sales profile for this booking.",
    )
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.SET_NULL,
        related_name="related_sales_booking",
        null=True,
        blank=True,
        help_text="Link to the associated payment record, if any (e.g., for deposit).",
    )

    sales_booking_reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="A unique reference code for the sales booking.",
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="The total amount paid for this booking (e.g., deposit or full payment).",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="unpaid",
        help_text="Current payment status of the booking (e.g., unpaid, deposit_paid, paid).",
    )
    currency = models.CharField(
        max_length=3,
        default="AUD",
        help_text="The three-letter ISO currency code for the booking (e.g., AUD).",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent associated with this booking, if applicable.",
    )
    request_viewing = models.BooleanField(
        default=False,
        help_text="Indicates if the customer specifically requested a viewing/test drive in a deposit-less enquiry flow.",
    )
    appointment_date = models.DateField(
        help_text="Confirmed date for the test drive, appointment, or pickup.",
        blank=True,
        null=True,
    )
    appointment_time = models.TimeField(
        help_text="Confirmed time for the test drive, appointment, or pickup.",
        blank=True,
        null=True,
    )

    booking_status = models.CharField(
        max_length=30,
        choices=BOOKING_STATUS_CHOICES,
        default="pending_confirmation",
        help_text="The current status of the sales booking (e.g., confirmed, reserved, enquired, completed).",
    )
    customer_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Any additional notes or messages provided by the customer.",
    )

    sales_terms_version = models.ForeignKey(
        "inventory.SalesTerms",
        on_delete=models.PROTECT, 
        related_name="sales_bookings", 
        null=True, 
        blank=True,
        help_text="The specific version of the T&Cs the user agreed to."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time when this sales booking was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The date and time when this sales booking was last updated.",
    )

    class Meta:
        verbose_name = "Sales Booking"
        verbose_name_plural = "Sales Bookings"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.sales_booking_reference:
            self.sales_booking_reference = f"SBK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Sales Booking {self.sales_booking_reference} for "
            f"{self.motorcycle.brand} {self.motorcycle.model} "
            f"(Status: {self.get_booking_status_display()})"
        )
