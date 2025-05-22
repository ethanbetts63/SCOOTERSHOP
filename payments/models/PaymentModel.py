# payments/models.py
from django.db import models
# REMOVED: from hire.models import TempHireBooking # This caused the circular import
from django.conf import settings # Needed for AUTH_USER_MODEL if we decide to link to user as well
import uuid # For UUIDField

class Payment(models.Model):
    """
    Represents a payment record associated with a temporary hire booking.
    This model stores details about the Stripe Payment Intent and other payment information.
    """
    # Use UUID as the primary key for global uniqueness
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Link directly to the TempHireBooking, ensuring a one-to-one relationship.
    # This is crucial for tying the payment to a specific booking.
    # CORRECTED: Using a string reference 'hire.TempHireBooking' to break the circular import.
    temp_hire_booking = models.OneToOneField(
        'hire.TempHireBooking', # Changed to string reference
        on_delete=models.CASCADE, # If the TempHireBooking is deleted, delete this Payment record too.
        related_name='payment', # Allows accessing payment from TempHireBooking: booking.payment
        help_text="The temporary hire booking associated with this payment."
    )

    # Optionally, link to the user who initiated the payment.
    # This can be useful for user-specific payment history, but the primary link is to the booking.
    # Make it nullable if payments can be made by unauthenticated users or if the user link isn't always available.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Don't delete payment if user is deleted, just set to NULL.
        related_name='payments',
        null=True, # Allow null if payment can be made without a logged-in user (e.g., guest checkout)
        blank=True,
        help_text="The user who made this payment, if applicable."
    )

    # The ID of the Stripe Payment Intent. This is crucial for tracking the payment on Stripe's side.
    stripe_payment_intent_id = models.CharField(
        max_length=100, # Stripe Payment Intent IDs are typically 27 characters (pi_...)
        unique=True, # Each Payment Intent ID should be unique.
        blank=True, # Allow blank/null initially, as it's populated after creation.
        null=True,
        help_text="The ID of the Stripe Payment Intent object."
    )

    # The ID of the Stripe Payment Method used (e.g., card ID). Useful for debugging or saved cards.
    stripe_payment_method_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Method used for this payment."
    )

    # The amount that was intended to be paid for this booking.
    # Using DecimalField for monetary values to avoid floating-point inaccuracies.
    amount = models.DecimalField(
        max_digits=10, # Maximum 10 digits in total (e.g., 99999999.99)
        decimal_places=2, # 2 decimal places for currency
        help_text="The amount of the payment."
    )

    # The currency of the payment (e.g., 'usd', 'eur', 'AUD').
    currency = models.CharField(
        max_length=3, # Standard currency codes are 3 letters (e.g., 'USD', 'AUD')
        default='AUD', 
        help_text="The three-letter ISO currency code (e.g., 'usd', 'AUD')."
    )

    # The current status of the payment. We will directly store Stripe's status strings.
    # This allows for full fidelity with Stripe's payment lifecycle.
    status = models.CharField(
        max_length=50, # Max length to accommodate various Stripe statuses
        default='requires_payment_method', # Initial status when created
        help_text="The current status of the Stripe Payment Intent (e.g., 'succeeded', 'requires_action')."
    )

    # A human-readable description for the payment, useful for Stripe dashboard.
    description = models.TextField(
        blank=True,
        null=True,
        help_text="A description for the payment, often sent to Stripe."
    )

    # JSON field to store any additional metadata, especially useful for Stripe.
    metadata = models.JSONField(
        default=dict, # Default to an empty dictionary
        blank=True,
        help_text="Arbitrary key-value pairs for additional payment information or Stripe metadata."
    )

    # Timestamps for when the record was created and last updated.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at'] # Order payments by creation date, newest first.

    def __str__(self):
        """
        String representation of the Payment object.
        """
        # Safely access temp_hire_booking ID, as it might be null
        temp_booking_id_str = str(self.temp_hire_booking.id) if self.temp_hire_booking else 'N/A'
        return f"Payment {self.id} for Booking {temp_booking_id_str} - Amount: {self.amount} {self.currency} - Status: {self.status}"
