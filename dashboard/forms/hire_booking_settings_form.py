from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import HireSettings # Import the new HireSettings model

class HireBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = HireSettings
        fields = [
            'default_daily_rate',
            'default_hourly_rate',
            'weekly_discount_percentage',
            'monthly_discount_percentage',
            'hire_pricing_strategy', # Added new pricing strategy field
            'excess_hours_margin', # Added new excess hours margin field
            'minimum_hire_duration_hours',
            'maximum_hire_duration_days',
            'booking_lead_time_hours',
            'pick_up_start_time',
            'pick_up_end_time',
            'return_off_start_time',
            'return_end_time',
            'deposit_enabled',
            'default_deposit_calculation_method',
            'deposit_percentage',
            'deposit_amount',
            'add_ons_enabled',
            'packages_enabled',
            'grace_period_minutes',
            'hire_confirmation_email_subject',
            'admin_hire_notification_email',
            'late_fee_per_day', # Retained as it's per day, not hourly
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
            # --- New Payment Option Fields ---
            'enable_online_full_payment',
            'enable_online_deposit_payment',
            'enable_in_store_full_payment',
            'enable_cash_payment',
            'enable_card_payment',
            'enable_other_payment',
        ]
        widgets = {
            'default_hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'default_daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'weekly_discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'monthly_discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'hire_pricing_strategy': forms.Select(attrs={'class': 'form-control'}), # Widget for new pricing strategy
            'excess_hours_margin': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}), # Widget for new excess hours margin
            'minimum_hire_duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'maximum_hire_duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'booking_lead_time_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'pick_up_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'pick_up_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'return_off_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'return_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'deposit_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_deposit_calculation_method': forms.Select(attrs={'class': 'form-control'}),
            'deposit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'add_ons_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'packages_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'grace_period_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'hire_confirmation_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'admin_hire_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
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
            # --- New Payment Option Widgets ---
            'enable_online_full_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_online_deposit_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_in_store_full_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_cash_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_card_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_other_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_hours = cleaned_data.get('minimum_hire_duration_hours') # Changed from min_days to min_hours
        max_days = cleaned_data.get('maximum_hire_duration_days')

        # Updated validation for minimum hire duration (hours) vs maximum hire duration (days)
        # It's difficult to directly compare hours and days without a conversion factor
        # For now, we'll keep the basic validation for max_days.
        # If a more complex comparison is needed (e.g., minimum hours cannot exceed X days),
        # it would require additional logic.
        if min_hours is not None and max_days is not None and (min_hours / 24) > max_days:
            self.add_error('minimum_hire_duration_hours', _("Minimum duration in hours cannot exceed maximum duration in days."))


        deposit_calculation_method = cleaned_data.get('default_deposit_calculation_method')
        deposit_percentage = cleaned_data.get('deposit_percentage')
        deposit_amount = cleaned_data.get('deposit_amount')
        deposit_enabled = cleaned_data.get('deposit_enabled')

        if deposit_enabled:
            if deposit_calculation_method == 'percentage' and (deposit_percentage is None or deposit_percentage < 0 or deposit_percentage > 100):
                self.add_error('deposit_percentage', _("Deposit percentage must be between 0 and 100 when using percentage calculation."))
            if deposit_calculation_method == 'fixed' and (deposit_amount is None or deposit_amount < 0):
                self.add_error('deposit_amount', _("Deposit amount must be a non-negative value when using fixed amount calculation."))

        pick_up_start_time = cleaned_data.get('pick_up_start_time')
        pick_up_end_time = cleaned_data.get('pick_up_end_time')
        return_off_start_time = cleaned_data.get('return_off_start_time')
        return_end_time = cleaned_data.get('return_end_time')

        if pick_up_start_time and pick_up_end_time and pick_up_start_time > pick_up_end_time:
            self.add_error('pick_up_end_time', _("Pick up end time must be after pick up start time."))

        if return_off_start_time and return_end_time and return_off_start_time > return_end_time:
            self.add_error('return_end_time', _("Return end time must be after return start time."))

        # --- Mutually exclusive validation for online deposit and in-store full payment ---
        enable_online_deposit = cleaned_data.get('enable_online_deposit_payment')
        enable_in_store_full = cleaned_data.get('enable_in_store_full_payment')

        if enable_online_deposit and enable_in_store_full:
            self.add_error('enable_online_deposit_payment', _("Cannot enable both online deposit and in-store full payment."))
            self.add_error('enable_in_store_full_payment', _("Cannot enable both online deposit and in-store full payment."))

        # Validation for excess_hours_margin based on hire_pricing_strategy
        hire_pricing_strategy = cleaned_data.get('hire_pricing_strategy')
        excess_hours_margin = cleaned_data.get('excess_hours_margin')

        if hire_pricing_strategy == '24_hour_plus_margin' and (excess_hours_margin is None or excess_hours_margin < 0):
            self.add_error('excess_hours_margin', _("Excess hours margin is required and must be a non-negative value for '24-Hour Billing with Margin' strategy."))
        elif hire_pricing_strategy != '24_hour_plus_margin' and excess_hours_margin is not None and excess_hours_margin > 0:
            # Optional: Clear the value if not relevant, or add a warning/error
            # For now, we'll just ensure it's not required if the strategy isn't '24_hour_plus_margin'
            pass


        return cleaned_data

