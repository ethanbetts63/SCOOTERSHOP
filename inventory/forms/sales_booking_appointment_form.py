from django import forms
from datetime import date, timedelta


class BookingAppointmentForm(forms.Form):
    appointment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Preferred Date",
        help_text="Choose your preferred date for the appointment.",
    )
    appointment_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Preferred Time",
        help_text="Choose your preferred time for the appointment.",
    )
    customer_notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
        label="Message to Admin",
        help_text="Any specific questions or requests for us. This will be sent to our admin along with your contact details.",
    )

    terms_accepted = forms.BooleanField(
        required=True,
        label="I accept the Terms and Conditions",
        widget=forms.CheckboxInput(),
    )

    def __init__(self, *args, **kwargs):
        self.deposit_required_for_flow = kwargs.pop("deposit_required_for_flow", False)
        self.inventory_settings = kwargs.pop("inventory_settings", None)
        super().__init__(*args, **kwargs)

        if self.deposit_required_for_flow:
            self.fields["appointment_date"].required = True
            self.fields["appointment_time"].required = True
        elif (
            self.inventory_settings
            and not self.inventory_settings.enable_viewing_for_enquiry
        ):
            self.fields["appointment_date"].widget = forms.HiddenInput()
            self.fields["appointment_time"].widget = forms.HiddenInput()
            self.fields["appointment_date"].required = False
            self.fields["appointment_time"].required = False

        if self.inventory_settings:

            min_date = date.today() + timedelta(
                hours=self.inventory_settings.min_advance_booking_hours
            )
            self.fields["appointment_date"].widget.attrs["min"] = min_date.strftime(
                "%Y-%m-%d"
            )

            max_date = date.today() + timedelta(
                days=self.inventory_settings.max_advance_booking_days
            )
            self.fields["appointment_date"].widget.attrs["max"] = max_date.strftime(
                "%Y-%m-%d"
            )

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get("appointment_date")
        appointment_time = cleaned_data.get("appointment_time")
        terms_accepted = cleaned_data.get("terms_accepted")

        is_appointment_required = self.deposit_required_for_flow 

        if is_appointment_required:
            if not appointment_date:
                self.add_error(
                    "appointment_date",
                    "This field is required for your selected option.",
                )
            if not appointment_time:
                self.add_error(
                    "appointment_time",
                    "This field is required for your selected option.",
                )
        else:

            cleaned_data["appointment_date"] = None
            cleaned_data["appointment_time"] = None

        if not terms_accepted:
            self.add_error(
                "terms_accepted", "You must accept the terms and conditions."
            )

        return cleaned_data
