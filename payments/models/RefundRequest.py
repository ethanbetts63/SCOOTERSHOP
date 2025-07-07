from django.db import models
from django.conf import settings
from payments.models.PaymentModel import Payment
import uuid
from django.utils import timezone


class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ("unverified", "Unverified - Awaiting Email Confirmation"),
        ("pending", "Pending Review"),
        ("reviewed_pending_approval", "Reviewed - Pending Approval"),
        ("approved", "Approved - Awaiting Refund"),
        ("rejected", "Rejected"),
        ("partially_refunded", "Partially Refunded"),
        ("refunded", "Refunded"),
        ("failed", "Refund Failed"),
    ]

    service_booking = models.ForeignKey(
        "service.ServiceBooking",
        on_delete=models.SET_NULL,
        related_name="refund_requests",
        null=True,
        blank=True,
        help_text="The service booking for which the refund is requested (if applicable).",
    )

    sales_booking = models.ForeignKey(
        "inventory.SalesBooking",
        on_delete=models.SET_NULL,
        related_name="refund_requests",
        null=True,
        blank=True,
        help_text="The sales booking for which the refund is requested (if applicable).",
    )

    service_profile = models.ForeignKey(
        "service.ServiceProfile",
        on_delete=models.SET_NULL,
        related_name="refund_requests_related_service_profile",
        null=True,
        blank=True,
        help_text="The service profile associated with this refund request (if applicable).",
    )

    sales_profile = models.ForeignKey(
        "inventory.SalesProfile",
        on_delete=models.SET_NULL,
        related_name="refund_requests_related_sales_profile",
        null=True,
        blank=True,
        help_text="The sales profile associated with this refund request (if applicable).",
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name="refund_requests",
        null=True,
        blank=True,
        help_text="The specific payment record associated with this refund request.",
    )

    reason = models.TextField(
        blank=True, help_text="Customer's reason for requesting the refund."
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason provided by staff for rejecting the refund request.",
    )
    requested_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the request was submitted."
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="unverified",
        help_text="Current status of the refund request.",
    )
    amount_to_refund = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The amount to be refunded, set by staff upon approval (can be partial).",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_refund_requests",
        help_text="Staff member who processed this request.",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the request was processed by staff.",
    )
    staff_notes = models.TextField(
        blank=True,
        help_text="Internal notes from staff regarding the processing of this request.",
    )
    stripe_refund_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Refund ID if the refund was processed via Stripe.",
    )
    is_admin_initiated = models.BooleanField(
        default=False,
        help_text="Indicates if this refund request was initiated by an administrator.",
    )
    refund_calculation_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores a snapshot of details used for refund calculation (e.g., policy applied, original amount, calculated refund amount).",
    )
    request_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address provided by the user for this refund request.",
    )

    verification_token = models.UUIDField(
        editable=False,
        unique=True,
        null=True,
        help_text="Unique token for email verification of the refund request.",
    )
    token_created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when the verification token was created.",
    )

    class Meta:
        verbose_name = "Refund Request"
        verbose_name_plural = "Refund Requests"
        ordering = ["-requested_at", "pk"]

    def __str__(self):
        booking_ref = "N/A"
        if self.service_booking:
            booking_ref = f"Booking {self.service_booking.service_booking_reference}"
        elif self.sales_booking:
            booking_ref = f"Sales Booking {self.sales_booking.sales_booking_reference}"
        return f"Refund Request for {booking_ref} - Status: {self.status}"

    def save(self, *args, **kwargs):

        if not self.verification_token:
            self.verification_token = uuid.uuid4()
        super().save(*args, **kwargs)
