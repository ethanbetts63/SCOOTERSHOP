                                               
from django import forms
from django.utils.translation import gettext_lazy as _
from payments.models import RefundPolicySettings

class RefundSettingsForm(forms.ModelForm):
    #--
    class Meta:
        model = RefundPolicySettings
        fields = [
                                              
            'cancellation_full_payment_full_refund_days',
            'cancellation_full_payment_partial_refund_days',
            'cancellation_full_payment_partial_refund_percentage',
            'cancellation_full_payment_minimal_refund_days',
            'cancellation_full_payment_minimal_refund_percentage',

                                         
            'cancellation_deposit_full_refund_days',
            'cancellation_deposit_partial_refund_days',
            'cancellation_deposit_partial_refund_percentage',
            'cancellation_deposit_minimal_refund_days',
            'cancellation_deposit_minimal_refund_percentage',

                                                        
            'sales_enable_deposit_refund_grace_period',
            'sales_deposit_refund_grace_period_hours',
            'sales_enable_deposit_refund',

                                 
            'refund_deducts_stripe_fee_policy',
            'stripe_fee_percentage_domestic',
            'stripe_fee_fixed_domestic',
            'stripe_fee_percentage_international',
            'stripe_fee_fixed_international',
        ]
        widgets = {
                                              
            'cancellation_full_payment_full_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_full_payment_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_full_payment_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'cancellation_full_payment_minimal_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_full_payment_minimal_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),

                                         
            'cancellation_deposit_full_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'cancellation_deposit_minimal_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_minimal_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),

                                                         
            'sales_enable_deposit_refund_grace_period': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sales_deposit_refund_grace_period_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'sales_enable_deposit_refund': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

                                 
            'refund_deducts_stripe_fee_policy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'stripe_fee_percentage_domestic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'max': '0.1'}),
            'stripe_fee_fixed_domestic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stripe_fee_percentage_international': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'max': '0.1'}),
            'stripe_fee_fixed_international': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
        labels = {
                          
            'cancellation_full_payment_full_refund_days': _("Full Payment: Full Refund Days"),
            'cancellation_full_payment_partial_refund_days': _("Full Payment: Partial Refund Days"),
            'cancellation_full_payment_partial_refund_percentage': _("Full Payment: Partial Refund Percentage (%)"),
            'cancellation_full_payment_minimal_refund_days': _("Full Payment: Minimal Refund Days"),
            'cancellation_full_payment_minimal_refund_percentage': _("Full Payment: Minimal Refund Percentage (%)"),

                     
            'cancellation_deposit_full_refund_days': _("Deposit: Full Refund Days"),
            'cancellation_deposit_partial_refund_days': _("Deposit: Partial Refund Days"),
            'cancellation_deposit_partial_refund_percentage': _("Deposit: Partial Refund Percentage (%)"),
            'cancellation_deposit_minimal_refund_days': _("Deposit: Minimal Refund Days"),
            'cancellation_deposit_minimal_refund_percentage': _("Deposit: Minimal Refund Percentage (%)"),

                                                        
            'sales_enable_deposit_refund_grace_period': _("Enable Deposit Refund Grace Period?"),
            'sales_deposit_refund_grace_period_hours': _("Deposit Refund Grace Period (Hours)"),
            'sales_enable_deposit_refund': _("Enable Global Deposit Refunds?"),

                         
            'refund_deducts_stripe_fee_policy': _("Deduct Stripe Fees on Refund?"),
            'stripe_fee_percentage_domestic': _("Stripe % Fee (Domestic)"),
            'stripe_fee_fixed_domestic': _("Stripe Fixed Fee (Domestic)"),
            'stripe_fee_percentage_international': _("Stripe % Fee (International)"),
            'stripe_fee_fixed_international': _("Stripe Fixed Fee (International)"),
        }
        help_texts = {
                          
            'cancellation_full_payment_full_refund_days': _("Number of full days before booking start for a full refund."),
            'cancellation_full_payment_partial_refund_days': _("Number of full days before booking start for a partial refund (less than full refund days)."),
            'cancellation_full_payment_partial_refund_percentage': _("Percentage of full payment to refund for partial cancellations."),
            'cancellation_full_payment_minimal_refund_days': _("Number of full days before booking start for a minimal refund (less than partial refund days)."),
            'cancellation_full_payment_minimal_refund_percentage': _("Percentage of full payment to refund for minimal cancellations."),

                     
            'cancellation_deposit_full_refund_days': _("Number of full days before booking start for a full deposit refund."),
            'cancellation_deposit_partial_refund_days': _("Number of full days before booking start for a partial deposit refund (less than full refund days)."),
            'cancellation_deposit_partial_refund_percentage': _("Percentage of deposit to refund for partial cancellations."),
            'cancellation_deposit_minimal_refund_days': _("Number of full days before booking start for a minimal deposit refund (less than partial refund days)."),
            'cancellation_deposit_minimal_refund_percentage': _("Percentage of deposit to refund for minimal cancellations."),

                                                            
            'sales_enable_deposit_refund_grace_period': _("Enable a grace period for deposit refunds after cancellation or decline."),
            'sales_deposit_refund_grace_period_hours': _("The number of hours within which a deposit can be refunded after cancellation or decline."),
            'sales_enable_deposit_refund': _("Globally enable or disable the ability to refund deposits."),

                         
            'refund_deducts_stripe_fee_policy': _("If checked, Stripe's transaction fees will be deducted from the refund amount."),
            'stripe_fee_percentage_domestic': _("Stripe's percentage fee for domestic card transactions (e.g., 0.0170 for 1.7%)."),
            'stripe_fee_fixed_domestic': _("Stripe's fixed fee for domestic card transactions (e.g., 0.30 for A$0.30)."),
            'stripe_fee_fixed_international': _("Stripe's fixed fee per transaction for international card transactions (e.g., 0.30 for A$0.30)."),
            'stripe_fee_percentage_international': _("Stripe's percentage fee for international card transactions (e.g., 0.0350 for 3.5%)."),
        }

    def clean(self):
                                                                                               
                                                                                                         
        cleaned_data = super().clean()
        try:
                                                                                                     
            instance = self.instance if self.instance.pk else RefundPolicySettings(**cleaned_data)
            instance.full_clean(exclude=['id'])                                                 
        except forms.ValidationError as e:
                                                                        
            self.add_error(None, e)                           
        return cleaned_data
