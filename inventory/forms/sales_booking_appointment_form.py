from django import forms
from datetime import date, timedelta

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
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label="Preferred Time",
        help_text="Choose your preferred time for the appointment."
    )
    customer_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        label="Message to Admin",
        help_text="Any specific questions or requests for us. This will be sent to our admin along with your contact details."
    )
    # New field for terms and conditions acceptance
    terms_accepted = forms.BooleanField(
        required=True,
        label="I accept the Terms and Conditions",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox h-4 w-4 text-indigo-600 rounded'}),
        error_messages={'required': "You must accept the terms and conditions to proceed."}
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

    def clean_request_viewing(self):
        # Convert 'yes'/'no' string to boolean True/False
        return self.cleaned_data['request_viewing'] == 'yes'

    def clean(self):
        cleaned_data = super().clean()
        request_viewing = cleaned_data.get('request_viewing') # This will now be a boolean due to clean_request_viewing
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')
        terms_accepted = cleaned_data.get('terms_accepted') # Get the new field

        # Determine if an appointment is truly required based on flow type or user's 'request_viewing' choice
        is_appointment_required = self.deposit_required_for_flow or \
                                  (request_viewing and self.inventory_settings and self.inventory_settings.enable_viewing_for_enquiry)

        if is_appointment_required:
            if not appointment_date:
                self.add_error('appointment_date', "This field is required for your selected option.")
            if not appointment_time:
                self.add_error('appointment_time', "This field is required for your selected option.")

        else:
            # If no appointment is required, clear any submitted date/time to avoid validation issues
            cleaned_data['appointment_date'] = None
            cleaned_data['appointment_time'] = None
        
        # Terms and conditions must always be accepted if present on the form (which it always will be now)
        if not terms_accepted:
            self.add_error('terms_accepted', "You must accept the terms and conditions.")

        return cleaned_data
