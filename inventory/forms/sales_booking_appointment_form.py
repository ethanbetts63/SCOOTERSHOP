# inventory/forms/sales_booking_appointment_form.py

from django import forms
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta, time

# Import the new validation utilities
from inventory.utils.validate_appointment_date import validate_appointment_date
from inventory.utils.validate_appointment_time import validate_appointment_time

class BookingAppointmentForm(forms.Form):
    # Changed to CharField with RadioSelect for 'Yes'/'No'
    request_viewing = forms.ChoiceField(
        choices=[('yes', 'Yes'), ('no', 'No')],
        widget=forms.RadioSelect(attrs={'class': 'form-radio h-4 w-4 text-indigo-600 transition duration-150 ease-in-out'}),
        initial='yes', # Default to 'Yes'
        required=True,
        label="I would like to book a viewing/test drive",
        help_text="Select 'Yes' to request a specific date and time for a viewing or test drive, or 'No' to submit a general enquiry."
    )
    appointment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Preferred Date",
        help_text="Choose your preferred date for the appointment."
    )
    appointment_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}), # This widget is actually ignored now as it's a select in HTML
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

        # If deposit is required, viewing is always implied/forced
        if self.deposit_required_for_flow:
            self.fields['request_viewing'].widget = forms.HiddenInput()
            self.fields['request_viewing'].initial = 'yes' # Force it to 'yes' internally
            self.fields['request_viewing'].required = False # Not required from user input perspective
            self.fields['appointment_date'].required = True
            self.fields['appointment_time'].required = True
        elif self.inventory_settings and not self.inventory_settings.enable_viewing_for_enquiry:
            # If viewing for enquiry is disabled, hide all appointment fields
            self.fields['request_viewing'].widget = forms.HiddenInput()
            self.fields['request_viewing'].initial = 'no' # Force it to 'no' internally
            self.fields['request_viewing'].required = False
            self.fields['appointment_date'].widget = forms.HiddenInput()
            self.fields['appointment_time'].widget = forms.HiddenInput()
            self.fields['appointment_date'].required = False
            self.fields['appointment_time'].required = False

        if self.inventory_settings:
            # Set min/max date attributes for the date picker
            min_date = date.today() + timedelta(hours=self.inventory_settings.min_advance_booking_hours)
            self.fields['appointment_date'].widget.attrs['min'] = min_date.strftime('%Y-%m-%d')

            max_date = date.today() + timedelta(days=self.inventory_settings.max_advance_booking_days)
            self.fields['appointment_date'].widget.attrs['max'] = max_date.strftime('%Y-%m-%d')

            # Time min/max are not directly used by the select field, but kept for potential reference
            # self.fields['appointment_time'].widget.attrs['min'] = self.inventory_settings.sales_appointment_start_time.strftime('%H:%M')
            # self.fields['appointment_time'].widget.attrs['max'] = self.inventory_settings.sales_appointment_end_time.strftime('%H:%M')

    def clean_request_viewing(self):
        # Convert 'yes'/'no' string to boolean True/False
        return self.cleaned_data['request_viewing'] == 'yes'

    def clean(self):
        cleaned_data = super().clean()
        request_viewing = cleaned_data.get('request_viewing') # This will now be a boolean due to clean_request_viewing
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')

        # Determine if an appointment is truly required based on flow type or user's 'request_viewing' choice
        is_appointment_required = self.deposit_required_for_flow or \
                                  (request_viewing and self.inventory_settings and self.inventory_settings.enable_viewing_for_enquiry)

        if is_appointment_required:
            if not appointment_date:
                self.add_error('appointment_date', "This field is required for your selected option.")
            if not appointment_time:
                self.add_error('appointment_time', "This field is required for your selected option.")

            # Only proceed with detailed validation if both fields are present and required
            if appointment_date and appointment_time: # No need for inventory_settings here, already checked by is_appointment_required
                # Call the date validation utility
                date_errors = validate_appointment_date(appointment_date, self.inventory_settings)
                for error in date_errors:
                    self.add_error('appointment_date', error)

                # Call the time validation utility
                time_errors = validate_appointment_time(appointment_date, appointment_time, self.inventory_settings)
                for error in time_errors:
                    self.add_error('appointment_time', error)
        else:
            # If no appointment is required, clear any submitted date/time to avoid validation issues
            cleaned_data['appointment_date'] = None
            cleaned_data['appointment_time'] = None

        return cleaned_data
