from django.db import models
import uuid
from decimal import Decimal

PAYMENT_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('deposit_paid', 'Deposit Paid'),
    ('paid', 'Fully Paid'),
    ('refunded', 'Refunded'),
]
BOOKING_STATUS_CHOICES = [
    ('pending_confirmation', 'Pending Confirmation'),
    ('confirmed', 'Confirmed'),
    ('cancelled', 'Cancelled'),
    ('declined', 'Declined by Admin'),
    ('completed', 'Completed'),
    ('no_show', 'No Show'),
    ('declined_refunded', 'Declined and Refunded'),
    ('reserved', 'Reserved'),
    ('enquired', 'Enquired'),
    ('pending_details', 'Pending Details')
]


class TempSalesBooking(models.Model):
    motorcycle = models.ForeignKey(
        'inventory.Motorcycle',
        on_delete=models.SET_NULL,
        related_name='temp_sales_bookings',
        null=True, blank=True,
        help_text="The motorcycle associated with this temporary sales booking."
    )
    sales_profile = models.ForeignKey(
        'inventory.SalesProfile',
        on_delete=models.CASCADE,
        related_name='temp_sales_bookings',
        null=True, blank=True,
        help_text="The customer's sales profile for this temporary booking."
    )
    payment = models.OneToOneField(
        'payments.Payment',
        on_delete=models.SET_NULL,
        related_name='related_temp_sales_booking',
        null=True, blank=True,
        help_text="Link to the associated payment record, if any (e.g., for deposit)."
    )

    session_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Unique identifier for retrieving the temporary booking.")
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="The amount paid for this booking (e.g., deposit amount). Defaults to 0."
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        help_text="Current payment status of the temporary booking (e.g., unpaid, deposit_paid)."
    )
    booking_status = models.CharField(
        max_length=30,
        choices=BOOKING_STATUS_CHOICES,
        default='pending_details',
        help_text="Current booking status (e.g., pending_confirmation, confirmed)."
    )
    currency = models.CharField(
        max_length=3,
        default='AUD',
        help_text="The three-letter ISO currency code for the booking (e.g., AUD)."
    )
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent associated with this booking, if applicable."
    )

    request_viewing = models.BooleanField(
        default=False,
        help_text="Indicates if the customer specifically requested a viewing/test drive in a deposit-less enquiry flow."
    )

    appointment_date = models.DateField(
        null=True, blank=True,
        help_text="Requested date for the test drive or appointment."
    )
    appointment_time = models.TimeField(
        null=True, blank=True,
        help_text="Requested time for the test drive or appointment."
    )

    customer_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Any additional notes or messages provided by the customer during the process."
    )
    terms_accepted = models.BooleanField(
        default=False,
        help_text="Indicates if the customer accepted the terms and conditions."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time when this temporary booking was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The date and time when this temporary booking was last updated."
    )

    deposit_required_for_flow = models.BooleanField(
        default=False,
        help_text="Indicates if this temporary booking initiated a flow requiring a deposit."
    )

    class Meta:
        verbose_name = "Temporary Sales Booking"
        verbose_name_plural = "Temporary Sales Bookings"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        motorcycle_display = (
            f" for {self.motorcycle.year} {self.motorcycle.brand} {self.motorcycle.model}"
            if self.motorcycle else ""
        )
        return (
            f"Temp Booking {self.session_uuid} {motorcycle_display} "
            f"(Status: {self.get_payment_status_display()})"
        )