from django import forms
from django.utils.translation import gettext_lazy as _
import datetime
from service.models import ServiceType

class ServiceTypeForm(forms.ModelForm):
    # These fields are for capturing days and hours separately in the form
    estimated_duration_days = forms.IntegerField(
        label="Estimated Duration (Days)",
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    estimated_duration_hours = forms.IntegerField(
        label="Estimated Duration (Hours)",
        min_value=0,
        max_value=23, # Assuming hours within a day
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '23'})
    )

    class Meta:
        model = ServiceType
        fields = ['name', 'description', 'base_price', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        days = cleaned_data.get('estimated_duration_days') or 0
        hours = cleaned_data.get('estimated_duration_hours') or 0

        # Ensure at least one duration field is provided if needed, or allow zero duration
        if days == 0 and hours == 0 and self.instance.pk is None:
             # self.add_error(None, _("Estimated duration (days or hours) is required."))
             pass # Allow zero duration for flexibility

        # Combine days and hours into a timedelta object
        # This calculated value will be assigned to the 'estimated_duration' field on the model instance
        cleaned_data['estimated_duration'] = datetime.timedelta(days=days, hours=hours)

        return cleaned_data