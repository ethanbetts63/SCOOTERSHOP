# In payments/HireRefundRequest.py

from django.db import models
from django.conf import settings # To link to Django's User model
from payments.models.PaymentModel import Payment # Import the Payment model
import uuid # Import uuid for the token
from django.utils import timezone # Import timezone for token_created_at

class HireRefundRequest(models.Model): # Renamed the model class
    STATUS_CHOICES = [
        ('unverified', 'Unverified - Awaiting Email Confirmation'),
        ('pending', 'Pending Review'),
        ('reviewed_pending_approval', 'Reviewed - Pending Approval'), # New status
        ('approved', 'Approved - Awaiting Refund'),
        ('rejected', 'Rejected'),
        ('partially_refunded', 'Partially Refunded'),
        ('refunded', 'Refunded'),
        ('failed', 'Refund Failed'),
    ]

    hire_booking = models.ForeignKey(
        'hire.HireBooking', # Use string reference to avoid circular import
        on_delete=models.CASCADE,
        related_name='refund_requests',
        help_text="The booking for which the refund is requested."
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name='refund_requests',
        null=True,
        blank=True,
        help_text="The specific payment record associated with this refund request."
    )

    driver_profile = models.ForeignKey(
        'hire.DriverProfile',
        on_delete=models.SET_NULL,
        related_name='refund_requests_related_driver',
        null=True,
        blank=True,
        help_text="The driver profile associated with this refund."
    )
    reason = models.TextField(
        blank=True,
        help_text="Customer's reason for requesting the refund."
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason provided by staff for rejecting the refund request."
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the request was submitted."
    )
    status = models.CharField(
        max_length=30, # Increased max_length to accommodate new status
        choices=STATUS_CHOICES,
        default='unverified',
        help_text="Current status of the refund request."
    )
    amount_to_refund = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The amount to be refunded, set by staff upon approval (can be partial)."
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refund_requests',
        help_text="Staff member who processed this request."
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the request was processed by staff."
    )
    staff_notes = models.TextField(
        blank=True,
        help_text="Internal notes from staff regarding the processing of this request."
    )
    stripe_refund_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Refund ID if the refund was processed via Stripe."
    )
    is_admin_initiated = models.BooleanField(
        default=False,
        help_text="Indicates if this refund request was initiated by an administrator."
    )
    refund_calculation_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores a snapshot of details used for refund calculation (e.g., policy applied, original amount, calculated refund amount)."
    )
    request_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address provided by the user for this refund request."
    )
    # NEW FIELDS for email verification
    verification_token = models.UUIDField(
        editable=False,
        unique=True,
        null=True,
        help_text="Unique token for email verification of the refund request."
    )
    token_created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when the verification token was created."
    )


    class Meta:
        verbose_name = "Hire Refund Request" # Updated verbose name
        verbose_name_plural = "Hire Refund Requests" # Updated verbose name plural
        ordering = ['-requested_at', 'pk'] # Added 'pk' as a secondary sort
        
    def __str__(self):
        return f"Refund Request for Booking {self.hire_booking.booking_reference if self.hire_booking else 'N/A'} - Status: {self.status}"

    def save(self, *args, **kwargs):
        # Generate a UUID for verification_token if it's not already set
        if not self.verification_token:
            self.verification_token = uuid.uuid4()
        super().save(*args, **kwargs)

