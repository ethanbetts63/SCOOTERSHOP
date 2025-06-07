# payments/models.py
from django.db import models
from django.conf import settings
import uuid

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    temp_hire_booking = models.OneToOneField(
        'hire.TempHireBooking',
        on_delete=models.SET_NULL,
        related_name='payment',
        null=True,
        blank=True,
        help_text="The temporary hire booking associated with this payment (null after conversion)."
    )

    hire_booking = models.ForeignKey(
        'hire.HireBooking',
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
        help_text="The permanent hire booking associated with this payment."
    )
    
    driver_profile = models.ForeignKey(
        'hire.DriverProfile',
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
        help_text="The driver profile associated with this payment."
    )

    temp_service_booking = models.OneToOneField(
        'service.TempServiceBooking',
        on_delete=models.SET_NULL,
        related_name='payment_for_temp_service', # Distinct related_name
        null=True,
        blank=True,
        help_text="The temporary service booking associated with this payment (null after conversion)."
    )

    service_booking = models.ForeignKey(
        'service.ServiceBooking',
        on_delete=models.SET_NULL,
        related_name='payments_for_service', # Distinct related_name
        null=True,
        blank=True,
        help_text="The permanent service booking associated with this payment."
    )

    service_customer_profile = models.ForeignKey(
        'service.ServiceProfile',
        on_delete=models.SET_NULL,
        related_name='payments_by_service_customer', # Distinct related_name
        null=True,
        blank=True,
        help_text="The service customer profile associated with this payment."
    )

    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent object."
    )

    stripe_payment_method_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Method used for this payment."
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The amount of the payment."
    )

    currency = models.CharField(
        max_length=3,
        default='AUD',
        help_text="The three-letter ISO currency code (e.g., 'usd', 'AUD')."
    )

    status = models.CharField(
        max_length=50,
        default='requires_payment_method',
        help_text="The current status of the Stripe Payment Intent (e.g., 'succeeded', 'requires_action')."
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="A description for the payment, often sent to Stripe."
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary key-value pairs for additional payment information or Stripe metadata."
    )

    refund_policy_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of refund policy settings from HireSettings at the time of booking."
    )

    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=True,
        blank=True,
        help_text="The total amount refunded for this payment."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']

    def __str__(self):
        temp_hire_booking_id_str = str(self.temp_hire_booking.id) if self.temp_hire_booking else 'N/A'
        hire_booking_ref_str = self.hire_booking.booking_reference if self.hire_booking else 'N/A'
        driver_profile_name = self.driver_profile.name if self.driver_profile else 'N/A'
        
        temp_service_booking_id_str = str(self.temp_service_booking.id) if self.temp_service_booking else 'N/A'
        service_booking_ref_str = self.service_booking.service_booking_reference if self.service_booking else 'N/A'
        service_customer_profile_name = self.service_customer_profile.name if self.service_customer_profile else 'N/A'

        return (
            f"Payment {self.id} "
            f"(TH: {temp_hire_booking_id_str}, H: {hire_booking_ref_str}, Driver: {driver_profile_name}; "
            f"TS: {temp_service_booking_id_str}, S: {service_booking_ref_str}, Service Cust: {service_customer_profile_name}) - "
            f"Amt: {self.amount} {self.currency} - Status: {self.status}"
        )
