# inventory/forms.py

from django import forms
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta, time

class BookingAppointmentForm(forms.Form):
    """
    Form for collecting appointment details and customer notes,
    used in the combined sales profile and booking details step.
    """
    # This field determines if the user wants to book a viewing for an enquiry.
    # It will be hidden if it's a reservation flow or if viewing is disabled globally.
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
        # Pop custom arguments before calling super().__init__
        self.deposit_required_for_flow = kwargs.pop('deposit_required_for_flow', False)
        self.inventory_settings = kwargs.pop('inventory_settings', None)
        super().__init__(*args, **kwargs)

        # If it's a reservation flow, 'request_viewing' is implicitly true and
        # appointment fields are always required. Hide the checkbox.
        if self.deposit_required_for_flow:
            self.fields['request_viewing'].widget = forms.HiddenInput()
            self.fields['request_viewing'].initial = True # Assume viewing for reservations
            self.fields['appointment_date'].required = True
            self.fields['appointment_time'].required = True
        # If it's an enquiry flow and viewing is NOT enabled in settings,
        # hide all appointment related fields.
        elif self.inventory_settings and not self.inventory_settings.enable_viewing_for_enquiry:
            self.fields['request_viewing'].widget = forms.HiddenInput()
            self.fields['appointment_date'].widget = forms.HiddenInput()
            self.fields['appointment_time'].widget = forms.HiddenInput()
            # Ensure they are not required if hidden
            self.fields['appointment_date'].required = False
            self.fields['appointment_time'].required = False

        # Add client-side validation hints (e.g., min/max dates)
        if self.inventory_settings:
            # Set minimum date for appointment_date
            min_date = date.today() + timedelta(hours=self.inventory_settings.min_advance_booking_hours)
            self.fields['appointment_date'].widget.attrs['min'] = min_date.strftime('%Y-%m-%d')

            # Set maximum date for appointment_date
            max_date = date.today() + timedelta(days=self.inventory_settings.max_advance_booking_days)
            self.fields['appointment_date'].widget.attrs['max'] = max_date.strftime('%Y-%m-%d')

            # Set min/max times
            self.fields['appointment_time'].widget.attrs['min'] = self.inventory_settings.sales_appointment_start_time.strftime('%H:%M')
            self.fields['appointment_time'].widget.attrs['max'] = self.inventory_settings.sales_appointment_end_time.strftime('%H:%M')


    def clean(self):
        cleaned_data = super().clean()
        request_viewing = cleaned_data.get('request_viewing')
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')

        # Determine if appointment fields are strictly required based on flow and user choice
        # They are required if it's a deposit-required flow OR
        # if it's an enquiry flow AND request_viewing is checked AND viewing is enabled in settings.
        is_appointment_required = self.deposit_required_for_flow or \
                                  (request_viewing and self.inventory_settings and self.inventory_settings.enable_viewing_for_enquiry)

        if is_appointment_required:
            if not appointment_date:
                self.add_error('appointment_date', "This field is required for your selected option.")
            if not appointment_time:
                self.add_error('appointment_time', "This field is required for your selected option.")

            # Perform detailed validation only if both date and time are provided and valid so far
            if appointment_date and appointment_time and self.inventory_settings:
                now = datetime.now()
                appointment_datetime = datetime.combine(appointment_date, appointment_time)

                # 1. Validate against min_advance_booking_hours
                min_advance_hours = self.inventory_settings.min_advance_booking_hours
                if appointment_datetime <= now + timedelta(hours=min_advance_hours):
                    self.add_error(
                        'appointment_date',
                        f"Appointments must be booked at least {min_advance_hours} hours in advance from now."
                    )
                    # Add error to time field as well for clarity to user
                    self.add_error(
                        'appointment_time',
                        f"Appointments must be booked at least {min_advance_hours} hours in advance from now."
                    )

                # 2. Validate against max_advance_booking_days
                max_advance_days = self.inventory_settings.max_advance_booking_days
                max_booking_date = date.today() + timedelta(days=max_advance_days)
                if appointment_date > max_booking_date:
                    self.add_error(
                        'appointment_date',
                        f"Appointments cannot be booked more than {max_advance_days} days in advance."
                    )

                # 3. Validate against sales_booking_open_days (day of the week)
                open_days_str = self.inventory_settings.sales_booking_open_days
                # Map abbreviated day names to Python's weekday() (0=Monday, 6=Sunday)
                open_days_map = {
                    'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
                }
                # Create a set of allowed weekday integers
                allowed_weekdays = {open_days_map[d.strip()] for d in open_days_str.split(',') if d.strip() in open_days_map}

                if appointment_date.weekday() not in allowed_weekdays:
                    self.add_error(
                        'appointment_date',
                        "Appointments are not available on the selected day of the week."
                    )

                # 4. Validate against sales_appointment_start_time and sales_appointment_end_time
                start_time = self.inventory_settings.sales_appointment_start_time
                end_time = self.inventory_settings.sales_appointment_end_time

                # Check if the appointment time falls within the allowed range
                if not (start_time <= appointment_time <= end_time):
                    self.add_error(
                        'appointment_time',
                        f"Appointments are only available between {start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')}."
                    )
        else:
            # If appointment is not required (e.g., enquiry without viewing request),
            # ensure appointment fields are explicitly cleared to avoid saving stale data.
            cleaned_data['appointment_date'] = None
            cleaned_data['appointment_time'] = None

        return cleaned_data
