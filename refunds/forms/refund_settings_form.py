from django import forms
from django.utils.translation import gettext_lazy as _
from refunds.models import RefundSettings


class RefundSettingsForm(forms.ModelForm):

    class Meta:
        model = RefundSettings
        fields = [
            "full_payment_full_refund_days",
            "full_payment_partial_refund_days",
            "full_payment_partial_refund_percentage",
            "full_payment_no_refund_percentage",
            "deposit_full_refund_days",
            "deposit_partial_refund_days",
            "deposit_partial_refund_percentage",
            "deposit_no_refund_days",
        ]
        widgets = {
            "full_payment_full_refund_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "full_payment_partial_refund_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "full_payment_partial_refund_percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
            "full_payment_no_refund_percentage": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "deposit_full_refund_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "deposit_partial_refund_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "deposit_partial_refund_percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
            "deposit_no_refund_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),

        }
        labels = {
            "full_payment_full_refund_days": _(
                "Full Payment: Full Refund Days"
            ),
            "full_payment_partial_refund_days": _(
                "Full Payment: Partial Refund Days"
            ),
            "full_payment_partial_refund_percentage": _(
                "Full Payment: Partial Refund Percentage (%)"
            ),
            "full_payment_no_refund_percentage": _(
                "Full Payment: No Refund Days"
            ),
            "deposit_full_refund_days": _("Deposit: Full Refund Days"),
            "deposit_partial_refund_days": _(
                "Deposit: Partial Refund Days"
            ),
            "deposit_partial_refund_percentage": _(
                "Deposit: Partial Refund Percentage (%)"
            ),
            "deposit_no_refund_days": _(
                "Deposit: No Refund Days"
            ),
            }
        help_texts = {
            "full_payment_full_refund_days": _(
                "Number of full days before booking start for a full refund."
            ),
            "full_payment_partial_refund_days": _(
                "Number of full days before booking start for a partial refund (less than full refund days)."
            ),
            "full_payment_partial_refund_percentage": _(
                "Percentage of full payment to refund for partial cancellations."
            ),
            "full_payment_no_refund_percentage": _(
                "Number of full days before booking start for a minimal refund (less than partial refund days)."
            ),
            "deposit_full_refund_days": _(
                "Number of full days before booking start for a full deposit refund."
            ),
            "deposit_partial_refund_days": _(
                "Number of full days before booking start for a partial deposit refund (less than full refund days)."
            ),
            "deposit_partial_refund_percentage": _(
                "Percentage of deposit to refund for partial cancellations."
            ),
            "deposit_no_refund_days": _(
                "Number of full days before booking start for a minimal deposit refund (less than partial refund days)."
            ),
        }

    def clean(self):

        cleaned_data = super().clean()
        try:

            instance = (
                self.instance
                if self.instance.pk
                else RefundSettings(**cleaned_data)
            )
            instance.full_clean(exclude=["id"])
        except forms.ValidationError as e:

            self.add_error(None, e)
        return cleaned_data
