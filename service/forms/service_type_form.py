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
        # Include 'estimated_duration' here if you want it to be handled by ModelForm's save,
        # but since we're manually setting it in clean/save, it's not strictly necessary
        # to list it here if it's not a direct form field.
        # However, for clarity and consistency, it's good practice to include all model fields
        # that the form is responsible for, even if indirectly.
        # In this case, we will manage 'estimated_duration' manually in the save method.
        fields = ['name', 'description', 'base_price', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If an instance is being edited, populate the duration fields from the instance's estimated_duration
        if self.instance and self.instance.pk and self.instance.estimated_duration is not None:
            total_seconds = int(self.instance.estimated_duration.total_seconds())
            days = total_seconds // (24 * 3600)
            hours = (total_seconds % (24 * 3600)) // 3600
            self.initial['estimated_duration_days'] = days
            self.initial['estimated_duration_hours'] = hours

    def clean(self):
        cleaned_data = super().clean()
        days = cleaned_data.get('estimated_duration_days') or 0
        hours = cleaned_data.get('estimated_duration_hours') or 0

        # Combine days and hours into a timedelta object
        # This calculated value will be assigned to the 'estimated_duration' field on the model instance
        # We allow zero duration as per the previous logic (commented out requirement check)
        cleaned_data['estimated_duration'] = datetime.timedelta(days=days, hours=hours)

        return cleaned_data

    def save(self, commit=True):
        # Create or get the instance, but don't save to DB yet
        instance = super().save(commit=False)

        # Assign the calculated estimated_duration from cleaned_data to the instance
        # This is crucial because 'estimated_duration' is not a direct form field
        # but is derived from 'estimated_duration_days' and 'estimated_duration_hours'.
        instance.estimated_duration = self.cleaned_data['estimated_duration']

        if commit:
            instance.save()
        return instance

