# payments/models.py
from django.db import models
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
    # Changed on_delete to SET_NULL to prevent accidental deletion of Payment when TempHireBooking is deleted.
    temp_hire_booking = models.OneToOneField(
        'hire.TempHireBooking', # Changed to string reference
        on_delete=models.SET_NULL, # IMPORTANT: Changed from CASCADE to SET_NULL
        related_name='payment', # Allows accessing payment from TempHireBooking: booking.payment
        null=True, # Allow null as TempHireBooking will be deleted after conversion
        blank=True, # Allow blank in forms
        help_text="The temporary hire booking associated with this payment (null after conversion)."
    )

    # NEW: Link to the permanent HireBooking after conversion.
    hire_booking = models.ForeignKey(
        'hire.HireBooking', # String reference to HireBooking model
        on_delete=models.SET_NULL, # If HireBooking is deleted, don't delete payment, just set to NULL.
        related_name='payments', # Allows accessing payments from HireBooking: booking.payments.all()
        null=True, # Will be set after successful conversion from TempHireBooking
        blank=True,
        help_text="The permanent hire booking associated with this payment."
    )

    # NEW: Link to the DriverProfile who made the payment.
    driver_profile = models.ForeignKey(
        'hire.DriverProfile', # String reference to DriverProfile model
        on_delete=models.SET_NULL, # If DriverProfile is deleted, don't delete payment.
        related_name='payments', # Allows accessing payments from DriverProfile: driver.payments.all()
        null=True, # Driver profile might not always be linked directly at payment creation
        blank=True,
        help_text="The driver profile associated with this payment."
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
        # Safely access related booking IDs for string representation
        temp_booking_id_str = str(self.temp_hire_booking.id) if self.temp_hire_booking else 'N/A'
        hire_booking_ref_str = self.hire_booking.booking_reference if self.hire_booking else 'N/A'
        return f"Payment {self.id} (Temp: {temp_booking_id_str}, Hire: {hire_booking_ref_str}) - Amount: {self.amount} {self.currency} - Status: {self.status}"

