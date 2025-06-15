# payments/forms/refund_policy_settings_form.py
from django import forms
from django.utils.translation import gettext_lazy as _
from payments.models import RefundPolicySettings

class RefundSettingsForm(forms.ModelForm):
    """
    Form for administrators to manage global Refund Policy Settings.
    This form includes all fields from the RefundPolicySettings model.
    """
    class Meta:
        model = RefundPolicySettings
        fields = [
            # Full Payment Cancellation Policy
            'cancellation_full_payment_full_refund_days',
            'cancellation_full_payment_partial_refund_days',
            'cancellation_full_payment_partial_refund_percentage',
            'cancellation_full_payment_minimal_refund_days',
            'cancellation_full_payment_minimal_refund_percentage',

            # Deposit Cancellation Policy
            'cancellation_deposit_full_refund_days',
            'cancellation_deposit_partial_refund_days',
            'cancellation_deposit_partial_refund_percentage',
            'cancellation_deposit_minimal_refund_days',
            'cancellation_deposit_minimal_refund_percentage',

            # Inventory app refund settings (NEW FIELDS)
            'sales_enable_deposit_refund_grace_period',
            'sales_deposit_refund_grace_period_hours',
            'sales_enable_deposit_refund',

            # Stripe Fee Settings
            'refund_deducts_stripe_fee_policy',
            'stripe_fee_percentage_domestic',
            'stripe_fee_fixed_domestic',
            'stripe_fee_percentage_international',
            'stripe_fee_fixed_international',
        ]
        widgets = {
            # Full Payment Cancellation Policy
            'cancellation_full_payment_full_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_full_payment_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_full_payment_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'cancellation_full_payment_minimal_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_full_payment_minimal_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),

            # Deposit Cancellation Policy
            'cancellation_deposit_full_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'cancellation_deposit_minimal_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_minimal_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),

            # Inventory app refund settings (NEW WIDGETS)
            'sales_enable_deposit_refund_grace_period': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sales_deposit_refund_grace_period_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'sales_enable_deposit_refund': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

            # Stripe Fee Settings
            'refund_deducts_stripe_fee_policy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'stripe_fee_percentage_domestic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'max': '0.1'}),
            'stripe_fee_fixed_domestic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stripe_fee_percentage_international': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'max': '0.1'}),
            'stripe_fee_fixed_international': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
        labels = {
            # Full Payment
            'cancellation_full_payment_full_refund_days': _("Full Payment: Full Refund Days"),
            'cancellation_full_payment_partial_refund_days': _("Full Payment: Partial Refund Days"),
            'cancellation_full_payment_partial_refund_percentage': _("Full Payment: Partial Refund Percentage (%)"),
            'cancellation_full_payment_minimal_refund_days': _("Full Payment: Minimal Refund Days"),
            'cancellation_full_payment_minimal_refund_percentage': _("Full Payment: Minimal Refund Percentage (%)"),

            # Deposit
            'cancellation_deposit_full_refund_days': _("Deposit: Full Refund Days"),
            'cancellation_deposit_partial_refund_days': _("Deposit: Partial Refund Days"),
            'cancellation_deposit_partial_refund_percentage': _("Deposit: Partial Refund Percentage (%)"),
            'cancellation_deposit_minimal_refund_days': _("Deposit: Minimal Refund Days"),
            'cancellation_deposit_minimal_refund_percentage': _("Deposit: Minimal Refund Percentage (%)"),

            # Inventory app refund settings (NEW LABELS)
            'sales_enable_deposit_refund_grace_period': _("Enable Deposit Refund Grace Period?"),
            'sales_deposit_refund_grace_period_hours': _("Deposit Refund Grace Period (Hours)"),
            'sales_enable_deposit_refund': _("Enable Global Deposit Refunds?"),

            # Stripe Fees
            'refund_deducts_stripe_fee_policy': _("Deduct Stripe Fees on Refund?"),
            'stripe_fee_percentage_domestic': _("Stripe % Fee (Domestic)"),
            'stripe_fee_fixed_domestic': _("Stripe Fixed Fee (Domestic)"),
            'stripe_fee_percentage_international': _("Stripe % Fee (International)"),
            'stripe_fee_fixed_international': _("Stripe Fixed Fee (International)"),
        }
        help_texts = {
            # Full Payment
            'cancellation_full_payment_full_refund_days': _("Number of full days before booking start for a full refund."),
            'cancellation_full_payment_partial_refund_days': _("Number of full days before booking start for a partial refund (less than full refund days)."),
            'cancellation_full_payment_partial_refund_percentage': _("Percentage of full payment to refund for partial cancellations."),
            'cancellation_full_payment_minimal_refund_days': _("Number of full days before booking start for a minimal refund (less than partial refund days)."),
            'cancellation_full_payment_minimal_refund_percentage': _("Percentage of full payment to refund for minimal cancellations."),

            # Deposit
            'cancellation_deposit_full_refund_days': _("Number of full days before booking start for a full deposit refund."),
            'cancellation_deposit_partial_refund_days': _("Number of full days before booking start for a partial deposit refund (less than full refund days)."),
            'cancellation_deposit_partial_refund_percentage': _("Percentage of deposit to refund for partial cancellations."),
            'cancellation_deposit_minimal_refund_days': _("Number of full days before booking start for a minimal deposit refund (less than partial refund days)."),
            'cancellation_deposit_minimal_refund_percentage': _("Percentage of deposit to refund for minimal cancellations."),

            # Inventory app refund settings (NEW HELP TEXTS)
            'sales_enable_deposit_refund_grace_period': _("Enable a grace period for deposit refunds after cancellation or decline."),
            'sales_deposit_refund_grace_period_hours': _("The number of hours within which a deposit can be refunded after cancellation or decline."),
            'sales_enable_deposit_refund': _("Globally enable or disable the ability to refund deposits."),

            # Stripe Fees
            'refund_deducts_stripe_fee_policy': _("If checked, Stripe's transaction fees will be deducted from the refund amount."),
            'stripe_fee_percentage_domestic': _("Stripe's percentage fee for domestic card transactions (e.g., 0.0170 for 1.7%)."),
            'stripe_fee_fixed_domestic': _("Stripe's fixed fee for domestic card transactions (e.g., 0.30 for A$0.30)."),
            'stripe_fee_fixed_international': _("Stripe's fixed fee per transaction for international card transactions (e.g., 0.30 for A$0.30)."),
            'stripe_fee_percentage_international': _("Stripe's percentage fee for international card transactions (e.g., 0.0350 for 3.5%)."),
        }

    def clean(self):
        # The RefundPolicySettings model already has a clean method for cross-field validation.
        # This form's clean method simply calls the superclass clean and then triggers the model's clean.
        cleaned_data = super().clean()
        try:
            # Create a temporary instance or use self.instance if it exists, to run model-level clean
            instance = self.instance if self.instance.pk else RefundPolicySettings(**cleaned_data)
            instance.full_clean(exclude=['id']) # Exclude 'id' as it's not a form field directly
        except forms.ValidationError as e:
            # Re-raise model validation errors as form validation errors
            self.add_error(None, e) # Add as a non-field error
        return cleaned_data
