
from django import forms
from service.models import ServiceType

class ServiceDetailsForm(forms.Form):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="Select a Service Type",
        label="Service Type",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    dropoff_date = forms.DateField(
        label="Preferred Date",
        # We will use Flatpickr for the date input in the template
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'text'}), 
        required=True
    )
    # Added a ChoiceField for dropoff time
    dropoff_time = forms.ChoiceField(
        label="Preferred Drop-off Time",
        choices=[], # Choices will be populated dynamically in the view
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )