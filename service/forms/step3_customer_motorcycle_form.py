from django import forms
from service.models import CustomerMotorcycle # Make sure this import path is correct

class CustomerMotorcycleForm(forms.ModelForm):
    """
    Form for collecting or updating detailed information about a customer's motorcycle.
    This form is used for:
    - Anonymous users providing their vehicle details.
    - Authenticated users adding a new motorcycle.
    - Authenticated users reviewing/updating details of an existing motorcycle.
    """
    other_brand_name = forms.CharField(
        label="Please specify brand name",
        required=False,
        max_length=100,
        help_text="Required if 'Other' is selected for brand.",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomerMotorcycle
        fields = [
            'brand',
            'make',
            'model',
            'year',
            'engine_size',
            'rego',
            'vin_number',
            'odometer',
            'transmission',
            'engine_number',
            'image',
            # 'other_brand_name' is added as an explicit field outside Meta.fields
            # because its required status is conditional.
        ]
        widgets = {
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'engine_size': forms.TextInput(attrs={'class': 'form-control'}), # or NumberInput if only numbers
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'odometer': forms.NumberInput(attrs={'class': 'form-control'}),
            'transmission': forms.TextInput(attrs={'class': 'form-control'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            'brand': 'Motorcycle Brand',
            'make': 'Make',
            'model': 'Model',
            'year': 'Year',
            'engine_size': 'Engine Size (e.g., 600cc, 1000cc)',
            'rego': 'Registration Number',
            'vin_number': 'VIN Number',
            'odometer': 'Odometer Reading (km)',
            'transmission': 'Transmission Type',
            'engine_number': 'Engine Number',
            'image': 'Motorcycle Image (Optional)',
        }

    def clean(self):
        """
        Custom clean method to handle conditional validation for 'other_brand_name'.
        """
        cleaned_data = super().clean()
        brand = cleaned_data.get('brand')
        other_brand_name = cleaned_data.get('other_brand_name')

        if brand == 'Other' and not other_brand_name:
            self.add_error('other_brand_name', "Please specify the brand name when 'Other' is selected.")
        elif brand != 'Other' and other_brand_name:
            # If a specific brand is chosen, clear 'other_brand_name' to avoid saving irrelevant data.
            cleaned_data['other_brand_name'] = ''

        return cleaned_data

    def save(self, commit=True):
        """
        Overrides the save method to handle the 'other_brand_name' logic
        before saving the instance to the database.
        """
        # Get the cleaned data before popping 'other_brand_name'
        brand_from_form = self.cleaned_data['brand']
        other_brand_name_from_form = self.cleaned_data.get('other_brand_name')

        # Create the instance without saving to the database yet
        # This will set all fields from Meta.fields
        instance = super().save(commit=False)

        # If 'Other' was selected for brand, use the value from 'other_brand_name'
        # for the model's 'brand' field.
        if brand_from_form == 'Other' and other_brand_name_from_form:
            instance.brand = other_brand_name_from_form
        # If a specific brand was chosen, instance.brand is already correctly set
        # from the 'brand' field in Meta.fields.

        if commit:
            instance.save()
            self.save_m2m() # Important for many-to-many fields, though not directly relevant here.
        return instance
