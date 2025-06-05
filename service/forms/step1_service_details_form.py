from django import forms
from service.models import ServiceType
from django.core.exceptions import ValidationError
from datetime import date

class ServiceDetailsForm(forms.Form):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="Select a Service Type",
        label="Service Type",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    service_date = forms.DateField( # Renamed from dropoff_date
        label="Service Date", # Updated label
        # We will use Flatpickr for the date input in the template
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'text'}),
        required=True
    )
    # Removed dropoff_time field

    def clean_service_date(self): # Renamed method
        """
        Custom validation for service_date to ensure it's not in the past.
        """
        service_date = self.cleaned_data['service_date'] # Updated field access
        current_date = date.today()
        if service_date < current_date:
            raise ValidationError("Service date cannot be in the past.")
        return service_date

