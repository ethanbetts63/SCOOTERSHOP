from django import forms
from django.utils.translation import gettext_lazy as _
# Import the new HireSettings model
# Assuming HireSettings is in your dashboard.models, adjust the import path if needed
from ..models import HireSettings

# Add 'default_hourly_rate' to the fields list
class HireBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = HireSettings
        fields = [
            'default_daily_rate',
            'default_weekly_rate',
            'default_monthly_rate',
            'default_hourly_rate', # Add this line
            'minimum_hire_duration_days',
            'maximum_hire_duration_days',
            'booking_lead_time_hours',
            'deposit_enabled',
            'default_deposit_calculation_method',
            'deposit_percentage',
            'deposit_amount',
            'add_ons_enabled',
            'packages_enabled',
            'grace_period_minutes',
            'hire_confirmation_email_subject',
            'admin_hire_notification_email',
            'late_fee_per_hour',
            'late_fee_per_day',
            'enable_cleaning_fee',
            'default_cleaning_fee',
            'minimum_driver_age',
            'young_driver_surcharge_age_limit',
            'require_driver_license_upload',
            'currency_code',
            'currency_symbol',
            'cancellation_full_refund_days',
            'cancellation_partial_refund_days',
            'cancellation_partial_refund_percentage',
            'cancellation_minimal_refund_days',
            'cancellation_minimal_refund_percentage',
        ]
        widgets = {
            # Add a widget for the new field
            'default_hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'default_daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'default_weekly_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'default_monthly_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'minimum_hire_duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'maximum_hire_duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'booking_lead_time_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'deposit_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_deposit_calculation_method': forms.Select(attrs={'class': 'form-control'}),
            'deposit_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01'
            }),
            'deposit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'add_ons_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'packages_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'grace_period_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'hire_confirmation_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'admin_hire_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'late_fee_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'late_fee_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'enable_cleaning_fee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_cleaning_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'minimum_driver_age': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'young_driver_surcharge_age_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'require_driver_license_upload': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '3'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '5'}),
            'cancellation_full_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'cancellation_minimal_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_minimal_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
        }

    # No need to add validation for default_hourly_rate in clean() unless you have specific requirements
    def clean(self):
        cleaned_data = super().clean()
        min_days = cleaned_data.get('minimum_hire_duration_days')
        max_days = cleaned_data.get('maximum_hire_duration_days')

        if min_days is not None and max_days is not None and min_days > max_days:
            self.add_error('minimum_hire_duration_days', _("Minimum duration must be less than or equal to maximum duration."))
            if not self.has_error('minimum_hire_duration_days'): # Check to avoid duplicate error messages
                 self.add_error('maximum_hire_duration_days', _("Maximum duration must be greater than or equal to minimum duration."))


        deposit_calculation_method = cleaned_data.get('default_deposit_calculation_method')
        deposit_percentage = cleaned_data.get('deposit_percentage')
        deposit_amount = cleaned_data.get('deposit_amount')

        if cleaned_data.get('deposit_enabled'):
            if deposit_calculation_method == 'percentage' and (deposit_percentage is None or deposit_percentage < 0 or deposit_percentage > 100):
                 self.add_error('deposit_percentage', _("Deposit percentage must be between 0 and 100 when using percentage calculation."))
            if deposit_calculation_method == 'fixed' and (deposit_amount is None or deposit_amount < 0):
                 self.add_error('deposit_amount', _("Deposit amount must be a non-negative value when using fixed amount calculation."))


        return cleaned_data