# inventory/forms/inventory_settings_form.py

from django import forms
from django.utils.translation import gettext_lazy as _
from inventory.models import InventorySettings # Ensure this import path is correct
from decimal import Decimal
from datetime import time

class InventorySettingsForm(forms.ModelForm):
    """
    Form for managing global inventory and sales system settings.
    """
    class Meta:
        model = InventorySettings
        fields = [
            'enable_sales_system',
            'enable_depositless_enquiry',
            'enable_reservation_by_deposit',
            'deposit_amount',
            'deposit_lifespan_days',
            'auto_refund_expired_deposits',
            'enable_sales_new_bikes',
            'enable_sales_used_bikes',
            'require_drivers_license',
            'require_address_info',
            'sales_booking_open_days',
            'sales_appointment_start_time',
            'sales_appointment_end_time',
            'sales_appointment_spacing_mins',
            'max_advance_booking_days',
            'min_advance_booking_hours',
            'currency_code',
            'currency_symbol',
            'terms_and_conditions_text',
        ]
        widgets = {
            'enable_sales_system': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_depositless_enquiry': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_reservation_by_deposit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'deposit_lifespan_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'auto_refund_expired_deposits': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_sales_new_bikes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_sales_used_bikes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'require_drivers_license': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'require_address_info': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sales_booking_open_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mon,Tue,Wed,Thu,Fri,Sat'}),
            'sales_appointment_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'sales_appointment_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'sales_appointment_spacing_mins': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_advance_booking_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'min_advance_booking_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '3', 'placeholder': 'e.g., AUD'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '5', 'placeholder': 'e.g., $'}),
            'terms_and_conditions_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def clean(self):
        """
        Custom validation for form fields, complementing model's clean method.
        """
        cleaned_data = super().clean()

        # Validate deposit_amount
        deposit_amount = cleaned_data.get('deposit_amount')
        if deposit_amount is not None and deposit_amount < Decimal('0.00'):
            self.add_error('deposit_amount', _("Deposit amount cannot be negative."))

        # Validate deposit_lifespan_days
        deposit_lifespan_days = cleaned_data.get('deposit_lifespan_days')
        if deposit_lifespan_days is not None and deposit_lifespan_days < 0:
            self.add_error('deposit_lifespan_days', _("Deposit lifespan days cannot be negative."))

        # Validate appointment times
        start_time = cleaned_data.get('sales_appointment_start_time')
        end_time = cleaned_data.get('sales_appointment_end_time')
        if start_time and end_time and start_time >= end_time:
            self.add_error('sales_appointment_start_time', _("Appointment start time must be earlier than end time."))
            self.add_error('sales_appointment_end_time', _("Appointment end time must be later than start time."))

        # Validate appointment spacing
        spacing_mins = cleaned_data.get('sales_appointment_spacing_mins')
        if spacing_mins is not None and spacing_mins <= 0:
            self.add_error('sales_appointment_spacing_mins', _("Appointment spacing must be a positive integer."))

        # Validate advance booking days
        max_days = cleaned_data.get('max_advance_booking_days')
        if max_days is not None and max_days < 0:
            self.add_error('max_advance_booking_days', _("Maximum advance booking days cannot be negative."))

        # Validate minimum advance booking hours
        min_hours = cleaned_data.get('min_advance_booking_hours')
        if min_hours is not None and min_hours < 0:
            self.add_error('min_advance_booking_hours', _("Minimum advance booking hours cannot be negative."))

        return cleaned_data
