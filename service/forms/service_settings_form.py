from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import ServiceSettings
from decimal import Decimal
from datetime import time # Import time for default values in tests if needed

class ServiceBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = ServiceSettings
        fields = [
            'enable_service_booking',
            'booking_advance_notice',
            'max_visible_slots_per_day',
            'allow_anonymous_bookings',
            'allow_account_bookings',
            'booking_open_days',
            'drop_off_start_time', 
            'drop_off_end_time', 
            'drop_off_spacing_mins', # New field
            'max_advance_dropoff_days', # New field
            'latest_same_day_dropoff_time', # Added this field
            'allow_after_hours_dropoff', # NEW FIELD
            'after_hours_dropoff_disclaimer', # NEW FIELD
            'enable_service_brands',
            'other_brand_policy_text',
            'enable_deposit',
            'deposit_calc_method',
            'deposit_flat_fee_amount',
            'deposit_percentage',
            'enable_online_full_payment',
            'enable_online_deposit',
            'enable_instore_full_payment',
            'currency_code',
            'currency_symbol',
            'cancel_full_payment_max_refund_days',
            'cancel_full_payment_max_refund_percentage',
            'cancel_full_payment_partial_refund_days',
            'cancel_full_payment_partial_refund_percentage',
            'cancel_full_payment_min_refund_days',
            'cancel_full_payment_min_refund_percentage',
            'cancellation_deposit_full_refund_days',
            'cancel_deposit_max_refund_percentage',
            'cancellation_deposit_partial_refund_days',
            'cancellation_deposit_partial_refund_percentage',
            'cancellation_deposit_minimal_refund_days',
            'cancellation_deposit_minimal_refund_percentage',
            'refund_deducts_stripe_fee_policy', # New field
            'stripe_fee_percentage_domestic', # New field
            'stripe_fee_fixed_domestic', # New field
            'stripe_fee_percentage_international', # New field
            'stripe_fee_fixed_international', # New field
        ]
        widgets = {
            'enable_service_booking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'booking_advance_notice': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_visible_slots_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'allow_anonymous_bookings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_account_bookings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'booking_open_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mon,Tue,Wed,Thu,Fri'}),
            'drop_off_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}), # Re-added
            'drop_off_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}), # Re-added
            'drop_off_spacing_mins': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '60'}), # New widget
            'max_advance_dropoff_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}), # New widget
            'latest_same_day_dropoff_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}), # Added widget
            'allow_after_hours_dropoff': forms.CheckboxInput(attrs={'class': 'form-check-input'}), # NEW WIDGET
            'after_hours_dropoff_disclaimer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), # NEW WIDGET
            'enable_service_brands': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'other_brand_policy_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'enable_deposit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposit_calc_method': forms.Select(attrs={'class': 'form-control'}),
            'deposit_flat_fee_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deposit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'enable_online_full_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_online_deposit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_instore_full_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
            'cancel_full_payment_max_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancel_full_payment_max_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'cancel_full_payment_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancel_full_payment_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'cancel_full_payment_min_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancel_full_payment_min_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'cancellation_deposit_full_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancel_deposit_max_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'cancellation_deposit_partial_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_partial_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'cancellation_deposit_minimal_refund_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cancellation_deposit_minimal_refund_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'}),
            'refund_deducts_stripe_fee_policy': forms.CheckboxInput(attrs={'class': 'form-check-input'}), # New widget
            'stripe_fee_percentage_domestic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'max': '0.1'}), # New widget
            'stripe_fee_fixed_domestic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}), # New widget
            'stripe_fee_percentage_international': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0', 'max': '0.1'}), # New widget
            'stripe_fee_fixed_international': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}), # New widget
        }

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get('drop_off_start_time')
        end_time = cleaned_data.get('drop_off_end_time')
        latest_same_day_dropoff = cleaned_data.get('latest_same_day_dropoff_time') # Get this from cleaned_data

        if start_time and end_time and start_time >= end_time:
            self.add_error('drop_off_start_time', _("Booking start time must be earlier than end time."))
            self.add_error('drop_off_end_time', _("Booking end time must be earlier than start time."))
        
        # Validate drop_off_spacing_mins
        drop_off_spacing_mins = cleaned_data.get('drop_off_spacing_mins')
        if drop_off_spacing_mins is not None and (drop_off_spacing_mins <= 0 or drop_off_spacing_mins > 60):
            self.add_error('drop_off_spacing_mins', _("Drop-off spacing must be a positive integer, typically between 1 and 60 minutes."))

        # Validate max_advance_dropoff_days
        max_advance_dropoff_days = cleaned_data.get('max_advance_dropoff_days')
        if max_advance_dropoff_days is not None and max_advance_dropoff_days < 0:
            self.add_error('max_advance_dropoff_days', _("Maximum advance drop-off days cannot be negative."))

        # Validate latest_same_day_dropoff_time is within drop_off_start_time and drop_off_end_time
        # This check is only relevant if after-hours drop-off is NOT allowed, or if it's the standard drop-off window.
        if latest_same_day_dropoff and start_time and end_time and (latest_same_day_dropoff < start_time or latest_same_day_dropoff > end_time):
            self.add_error('latest_same_day_dropoff_time', _(f"Latest same-day drop-off time must be between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}, inclusive."))

        # Validate refund percentages
        refund_percentage_fields = [
            'deposit_percentage',
            'cancel_full_payment_max_refund_percentage', 'cancel_full_payment_partial_refund_percentage', 'cancel_full_payment_min_refund_percentage',
            'cancel_deposit_max_refund_percentage', 'cancellation_deposit_partial_refund_percentage', 'cancellation_deposit_minimal_refund_percentage',
        ]
        for field_name in refund_percentage_fields:
            value = cleaned_data.get(field_name)
            if value is not None and not (Decimal('0.00') <= value <= Decimal('1.00')):
                self.add_error(field_name, _(f"Ensure {field_name.replace('_', ' ')} is between 0.00 (0%) and 1.00 (100%)."))

        # Validate Stripe fee percentages
        stripe_fee_percentage_domestic = cleaned_data.get('stripe_fee_percentage_domestic')
        if stripe_fee_percentage_domestic is not None and not (Decimal('0.00') <= stripe_fee_percentage_domestic <= Decimal('0.10')):
            self.add_error('stripe_fee_percentage_domestic', _("Ensure domestic stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."))

        stripe_fee_percentage_international = cleaned_data.get('stripe_fee_percentage_international')
        if stripe_fee_percentage_international is not None and not (Decimal('0.00') <= stripe_fee_percentage_international <= Decimal('0.10')):
            self.add_error('stripe_fee_percentage_international', _("Ensure international stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."))

        # Add cross-field validation for refund days (max > partial > min)
        # Full payment refund days
        max_full_days = cleaned_data.get('cancel_full_payment_max_refund_days')
        partial_full_days = cleaned_data.get('cancel_full_payment_partial_refund_days')
        min_full_days = cleaned_data.get('cancel_full_payment_min_refund_days')

        if max_full_days is not None and partial_full_days is not None and max_full_days < partial_full_days:
            self.add_error('cancel_full_payment_max_refund_days', _("Max refund days must be greater than or equal to partial refund days."))
        if partial_full_days is not None and min_full_days is not None and partial_full_days < min_full_days:
            self.add_error('cancel_full_payment_partial_refund_days', _("Partial refund days must be greater than or equal to min refund days."))

        # Deposit refund days
        max_deposit_days = cleaned_data.get('cancellation_deposit_full_refund_days')
        partial_deposit_days = cleaned_data.get('cancellation_deposit_partial_refund_days')
        min_deposit_days = cleaned_data.get('cancellation_deposit_minimal_refund_days')

        if max_deposit_days is not None and partial_deposit_days is not None and max_deposit_days < partial_deposit_days:
            self.add_error('cancellation_deposit_full_refund_days', _("Max deposit refund days must be greater than or equal to partial deposit refund days."))
        if partial_deposit_days is not None and min_deposit_days is not None and partial_deposit_days < min_deposit_days:
            self.add_error('cancellation_deposit_partial_refund_days', _("Partial deposit refund days must be greater than or equal to min deposit refund days."))


        return cleaned_data

