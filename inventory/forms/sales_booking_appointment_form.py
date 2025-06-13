# inventory/forms/sales_booking_appointment_form.py

from django import forms
from datetime import date, timedelta
from inventory.utils.validate_appointment_date import validate_appointment_date
from inventory.utils.validate_appointment_time import validate_appointment_time

class BookingAppointmentForm(forms.Form):
    request_viewing = forms.BooleanField(
        required=False,
        label="I would like to book a viewing/test drive",
        help_text="Select this option to request a specific date and time for a viewing or test drive."
    )
    appointment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Preferred Date",
        help_text="Choose your preferred date for the appointment."
    )
    appointment_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label="Preferred Time",
        help_text="Choose your preferred time for the appointment."
    )
    customer_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Additional Notes",
        help_text="Any specific requests or information for us."
    )

    def __init__(self, *args, **kwargs):
        self.deposit_required_for_flow = kwargs.pop('deposit_required_for_flow', False)
        self.inventory_settings = kwargs.pop('inventory_settings', None)
        super().__init__(*args, **kwargs)

        if self.deposit_required_for_flow:
            self.fields['request_viewing'].widget = forms.HiddenInput()
            self.fields['request_viewing'].initial = True
            self.fields['appointment_date'].required = True
            self.fields['appointment_time'].required = True
        elif self.inventory_settings and not self.inventory_settings.enable_viewing_for_enquiry:
            self.fields['request_viewing'].widget = forms.HiddenInput()
            self.fields['appointment_date'].widget = forms.HiddenInput()
            self.fields['appointment_time'].widget = forms.HiddenInput()
            self.fields['appointment_date'].required = False
            self.fields['appointment_time'].required = False

        if self.inventory_settings:
            min_date = date.today() + timedelta(hours=self.inventory_settings.min_advance_booking_hours)
            self.fields['appointment_date'].widget.attrs['min'] = min_date.strftime('%Y-%m-%d')

            max_date = date.today() + timedelta(days=self.inventory_settings.max_advance_booking_days)
            self.fields['appointment_date'].widget.attrs['max'] = max_date.strftime('%Y-%m-%d')

            self.fields['appointment_time'].widget.attrs['min'] = self.inventory_settings.sales_appointment_start_time.strftime('%H:%M')
            self.fields['appointment_time'].widget.attrs['max'] = self.inventory_settings.sales_appointment_end_time.strftime('%H:%M') # Re-added max attribute


    def clean(self):
        cleaned_data = super().clean()
        request_viewing = cleaned_data.get('request_viewing')
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')

        is_appointment_required = self.deposit_required_for_flow or \
                                  (request_viewing and self.inventory_settings and self.inventory_settings.enable_viewing_for_enquiry)

        if is_appointment_required:
            if not appointment_date:
                self.add_error('appointment_date', "This field is required for your selected option.")
            if not appointment_time:
                self.add_error('appointment_time', "This field is required for your selected option.")

            # Only proceed with detailed validation if both fields are present
            if appointment_date and appointment_time and self.inventory_settings:
                # Call the date validation utility
                date_errors = validate_appointment_date(appointment_date, self.inventory_settings)
                for error in date_errors:
                    self.add_error('appointment_date', error)

                # Call the time validation utility
                time_errors = validate_appointment_time(appointment_date, appointment_time, self.inventory_settings)
                for error in time_errors:
                    self.add_error('appointment_time', error)
        else:
            cleaned_data['appointment_date'] = None
            cleaned_data['appointment_time'] = None

        return cleaned_data
