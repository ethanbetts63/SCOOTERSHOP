from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal

from payments.models import RefundPolicySettings


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    temp_service_booking = models.OneToOneField(
        "service.TempServiceBooking",
        on_delete=models.SET_NULL,
        related_name="payment_for_temp_service",
        null=True,
        blank=True,
        help_text="The temporary service booking associated with this payment (null after conversion).",
    )

    service_booking = models.ForeignKey(
        "service.ServiceBooking",
        on_delete=models.SET_NULL,
        related_name="payments_for_service",
        null=True,
        blank=True,
        help_text="The permanent service booking associated with this payment.",
    )

    service_customer_profile = models.ForeignKey(
        "service.ServiceProfile",
        on_delete=models.SET_NULL,
        related_name="payments_by_service_customer",
        null=True,
        blank=True,
        help_text="The service customer profile associated with this payment.",
    )

    temp_sales_booking = models.OneToOneField(
        "inventory.TempSalesBooking",
        on_delete=models.SET_NULL,
        related_name="payment_from_sales_temp_link",
        null=True,
        blank=True,
        help_text="The temporary sales booking associated with this payment (null after conversion).",
    )

    sales_booking = models.ForeignKey(
        "inventory.SalesBooking",
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
        help_text="The permanent sales booking associated with this payment.",
    )

    sales_customer_profile = models.ForeignKey(
        "inventory.SalesProfile",
        on_delete=models.SET_NULL,
        related_name="payments_by_sales_customer",
        null=True,
        blank=True,
        help_text="The sales customer profile associated with this payment.",
    )

    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent object.",
    )

    stripe_payment_method_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Method used for this payment.",
    )

    amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="The amount of the payment."
    )

    currency = models.CharField(
        max_length=3,
        default="AUD",
        help_text="The three-letter ISO currency code (e.g., 'usd', 'AUD').",
    )

    status = models.CharField(
        max_length=50,
        default="requires_payment_method",
        help_text="The current status of the Stripe Payment Intent (e.g., 'succeeded', 'requires_action').",
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="A description for the payment, often sent to Stripe.",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary key-value pairs for additional payment information or Stripe metadata.",
    )

    refund_policy_snapshot = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Snapshot of refund policy settings from RefundPolicySettings at the time of payment.",
    )

    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=True,
        blank=True,
        help_text="The total amount refunded for this payment.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):

        return f"Payment {self.id} - {self.amount} {self.currency} - {self.status}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
