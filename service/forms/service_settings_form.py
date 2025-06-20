# service/forms/service_settings_form.py

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
            'drop_off_spacing_mins',
            'max_advance_dropoff_days',
            'latest_same_day_dropoff_time',
            'allow_after_hours_dropoff',
            'after_hours_dropoff_disclaimer',
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
        ]
        widgets = {
            'enable_service_booking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'booking_advance_notice': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_visible_slots_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'allow_anonymous_bookings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_account_bookings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'booking_open_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mon,Tue,Wed,Thu,Fri'}),
            'drop_off_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'drop_off_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'drop_off_spacing_mins': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '60'}),
            'max_advance_dropoff_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'latest_same_day_dropoff_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'allow_after_hours_dropoff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'after_hours_dropoff_disclaimer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'enable_service_brands': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'other_brand_policy_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'enable_deposit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposit_calc_method': forms.Select(attrs={'class': 'form-control'}),
            'deposit_flat_fee_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            # Corrected max value for deposit_percentage to 100 to match model validation
            'deposit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'enable_online_full_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_online_deposit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_instore_full_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get('drop_off_start_time')
        end_time = cleaned_data.get('drop_off_end_time')
        latest_same_day_dropoff = cleaned_data.get('latest_same_day_dropoff_time')

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
        if latest_same_day_dropoff and start_time and end_time and (latest_same_day_dropoff < start_time or latest_same_day_dropoff > end_time):
            self.add_error('latest_same_day_dropoff_time', _(f"Latest same-day drop-off time must be between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}, inclusive."))

        # Only validate deposit_percentage here, as other refund percentages are now in RefundPolicySettings
        deposit_percentage = cleaned_data.get('deposit_percentage')
        if deposit_percentage is not None and not (Decimal('0.00') <= deposit_percentage <= Decimal('100.00')):
            self.add_error('deposit_percentage', _(f"Ensure deposit percentage is between 0.00% and 100.00%."))

        return cleaned_data
