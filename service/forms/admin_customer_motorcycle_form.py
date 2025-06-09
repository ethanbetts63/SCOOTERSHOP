from django import forms
from service.models import CustomerMotorcycle, ServiceProfile

class AdminCustomerMotorcycleForm(forms.ModelForm):
    """
    Form for administrators to create and manage CustomerMotorcycle instances.
    Includes a field to link an existing ServiceProfile.
    """
    service_profile = forms.ModelChoiceField(
        queryset=ServiceProfile.objects.all().order_by('name', 'email'), # Order by name and email for easy selection
        required=False, # Make linking to a profile optional for creation, but can be set by admin
        empty_label="-- No Service Profile --", # Option to select no service profile
        help_text="Optionally link this motorcycle to an existing Service Profile.",
        widget=forms.Select(attrs={'class': 'form-control'}) # Apply basic Bootstrap styling
    )

    class Meta:
        model = CustomerMotorcycle
        fields = [
            'service_profile', # Link to ServiceProfile
            'brand',
            'model',
            'year',
            'rego',
            'odometer',
            'transmission',
            'engine_size',
            'vin_number',
            'engine_number',
            'image', # Include image field
        ]
        widgets = {
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1900}), # Add min year for better UX
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'odometer': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}), # Add min odometer for better UX
            'transmission': forms.Select(attrs={'class': 'form-control'}),
            'engine_size': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'service_profile': 'Linked Service Profile',
            'brand': 'Brand',
            'model': 'Model',
            'year': 'Year',
            'rego': 'Registration Number',
            'odometer': 'Odometer (km)',
            'transmission': 'Transmission Type',
            'engine_size': 'Engine Size',
            'vin_number': 'VIN Number (Optional)',
            'engine_number': 'Engine Number (Optional)',
            'image': 'Motorcycle Image (Optional)',
        }

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data
