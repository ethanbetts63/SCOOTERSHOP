from django import forms
from service.models import ServiceType
from django.core.exceptions import ValidationError
from datetime import date


class ServiceDetailsForm(forms.Form):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="Select Service Type",
        label="Service Type",
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
    )
    service_date = forms.DateField(
        label="Service Date",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "text"}),
        required=True,
    )

    def clean_service_date(self):

        service_date = self.cleaned_data["service_date"]
        current_date = date.today()
        if service_date < current_date:
            raise ValidationError("Service date cannot be in the past.")
        return service_date
