from django.db import models, transaction
from django.core.exceptions import ValidationError

DEFAULT_REFUND_POLICY_CONTENT = """
# Refund Policy

## Deposits

### Full Refund
- **Eligibility:** Cancellations made more than [X] days before the scheduled service or pickup date.
- **Process:** The full deposit amount will be refunded to the original payment method.

### Partial Refund
- **Eligibility:** Cancellations made between [Y] and [X] days before the scheduled date.
- **Refund Amount:** [Z]% of the deposit will be refunded.
- **Process:** The partial refund will be processed to the original payment method.

### No Refund
- **Eligibility:** Cancellations made less than [Y] days before the scheduled date.
- **Outcome:** The deposit is non-refundable.

## Full Payments

### Full Refund
- **Eligibility:** Cancellations made more than [A] days before the scheduled service or pickup date.
- **Process:** The full payment amount will be refunded to the original payment method.

### Partial Refund
- **Eligibility:** Cancellations made between [B] and [A] days before the scheduled date.
- **Refund Amount:** [C]% of the total payment will be refunded.
- **Process:** The partial refund will be processed to the original payment method.

### No Refund
- **Eligibility:** Cancellations made less than [B] days before the scheduled date.
- **Outcome:** The payment is non-refundable.
"""

class RefundTerms(models.Model):
    # Deposit Refund Settings
    deposit_full_refund_days = models.PositiveIntegerField(default=14)
    deposit_partial_refund_days = models.PositiveIntegerField(default=7)
    deposit_partial_refund_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    deposit_no_refund_days = models.PositiveIntegerField(default=2)

    # Full Payment Refund Settings
    full_payment_full_refund_days = models.PositiveIntegerField(default=14)
    full_payment_partial_refund_days = models.PositiveIntegerField(default=7)
    full_payment_partial_refund_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    full_payment_no_refund_days = models.PositiveIntegerField(default=2)

    # Versioned Policy Text
    content = models.TextField(default=DEFAULT_REFUND_POLICY_CONTENT)
    version_number = models.PositiveIntegerField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Refund Policy"
        verbose_name_plural = "Refund Policies"
        ordering = ['-version_number']

    def __str__(self):
        status = 'Active' if self.is_active else 'Archived'
        return f"v{self.version_number} - Created: {self.created_at.strftime('%d %b %Y')} ({status})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.version_number:
            last_version = RefundTerms.objects.all().order_by('version_number').last()
            self.version_number = (last_version.version_number + 1) if last_version else 1

        if self.is_active:
            with transaction.atomic():
                RefundTerms.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)

    def clean(self):
        if not self.is_active and not RefundTerms.objects.filter(is_active=True).exclude(pk=self.pk).exists():
             raise ValidationError("You cannot deactivate the only active refund policy version. Please activate another version first.")
