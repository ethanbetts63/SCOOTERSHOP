# In payments/HireRefundRequest.py

from django.db import models
from django.conf import settings # To link to Django's User model
from hire.models import HireBooking 
from payments.models import Payment

class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved - Awaiting Refund'), # Approved by staff, but Stripe refund not yet initiated
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'), # Stripe refund successfully processed
        ('failed', 'Refund Failed'), # Stripe refund initiated but failed
    ]

    hire_booking = models.ForeignKey(
        HireBooking,
        on_delete=models.CASCADE,
        related_name='refund_requests',
        help_text="The booking for which the refund is requested."
    )

    driver_profile = models.ForeignKey(
        'hire.DriverProfile',
        on_delete=models.SET_NULL, 
        related_name='payments', 
        null=False, 
        blank=False,
        help_text="The driver profile associated with this refund."
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL, # If the payment record is deleted, don't delete the refund request
        related_name='refund_requests',
        null=True,
        blank=True,
        help_text="The specific payment record associated with this refund request."
    )
    reason = models.TextField(
        help_text="Customer's reason for requesting the refund."
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the request was submitted."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the refund request."
    )
    amount_to_refund = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The amount to be refunded, set by staff upon approval (can be partial)."
    )
    refund_calculation_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores a snapshot of details used for refund calculation (e.g., policy applied, original amount, calculated refund amount)."
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
    is_admin_initiated = models.BooleanField(
        default=False,
        help_text="Indicates if this refund request was initiated by an administrator."
    )
    stripe_refund_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Refund ID if the refund was processed via Stripe."
    )

    class Meta:
        verbose_name = "Refund Request"
        verbose_name_plural = "Refund Requests"
        ordering = ['-requested_at']

    def __str__(self):
        return f"Refund Request for Booking {self.hire_booking.id} - Status: {self.status}"