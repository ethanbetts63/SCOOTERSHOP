from django import forms
from service.models import CustomerMotorcycle, ServiceBrand
from django.utils.translation import gettext_lazy as _

class CustomerMotorcycleForm(forms.ModelForm):
    """
    Form for collecting or updating detailed information about a customer's motorcycle.
    This form is used for:
    - Anonymous users providing their vehicle details.
    - Authenticated users adding a new motorcycle.
    - Authenticated users reviewing/updating details of an existing motorcycle.
    """
    other_brand_name = forms.CharField(
        label=_("Please specify brand name"),
        required=False,
        max_length=100,
        help_text=_("Required if 'Other' is selected for brand."),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    brand = forms.ChoiceField(
        label=_("Motorcycle Brand"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_("Select the brand of your motorcycle. Choose 'Other' if your brand is not listed."),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get all existing ServiceBrand names
        brand_names = [brand.name for brand in ServiceBrand.objects.all().order_by('name')]
        
        # Prepare choices for the 'brand' field
        # Add the '-- Select Brand --' option at the beginning
        brand_choices = [('', _('-- Select Brand --'))] + [(name, name) for name in brand_names]
        brand_choices.append(('Other', _('Other (please specify)')))

        self.fields['brand'].choices = brand_choices

        # Handle initialization for existing instance
        if self.instance and self.instance.pk: # Check if it's an existing instance
            # Check if the instance's brand is one of the known ServiceBrands
            if self.instance.brand in brand_names:
                self.initial['brand'] = self.instance.brand
                self.initial['other_brand_name'] = '' # Ensure it's empty
            else:
                # If the instance's brand is not in known ServiceBrands, it must be an "Other" brand
                self.initial['brand'] = 'Other'
                self.initial['other_brand_name'] = self.instance.brand # Populate the 'other_brand_name' field


    class Meta:
        model = CustomerMotorcycle
        fields = [
            'brand',
            # Removed 'make' field
            'model',
            'year',
            'engine_size',
            'rego',
            'vin_number',
            'odometer',
            'transmission',
            'engine_number',
            'image',
        ]
        widgets = {
            # Removed 'make' widget
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'engine_size': forms.TextInput(attrs={'class': 'form-control'}),
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'odometer': forms.NumberInput(attrs={'class': 'form-control'}),
            'transmission': forms.Select(attrs={'class': 'form-control'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            # Removed 'make' label
            'model': _('Model'),
            'year': _('Year'),
            'engine_size': _('Engine Size'),
            'rego': _('Registration Number'),
            'vin_number': _('VIN Number'),
            'odometer': _('Odometer Reading (km)'),
            'transmission': _('Transmission Type'),
            'engine_number': _('Engine Number'),
            'image': _('Motorcycle Image (Optional)'),
        }

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get('brand')
        other_brand_name = cleaned_data.get('other_brand_name')

        # If 'Other' is selected, other_brand_name must be provided
        if brand == 'Other' and not other_brand_name:
            self.add_error('other_brand_name', _("Please specify the brand name when 'Other' is selected."))
        # If a specific brand is chosen, ensure other_brand_name is cleared
        elif brand != 'Other' and other_brand_name:
            cleaned_data['other_brand_name'] = ''
        # If '-- Select Brand --' is chosen and it's a required field, add an error
        # Assuming 'brand' is required, Django's default validation will handle it if the field is empty.
        # However, if it's not required, or for explicit validation, you might add:
        # if not brand:
        #     self.add_error('brand', _("Please select a motorcycle brand."))

        return cleaned_data

    def save(self, commit=True):
        brand_from_form = self.cleaned_data['brand']
        other_brand_name_from_form = self.cleaned_data.get('other_brand_name')

        instance = super().save(commit=False)

        if brand_from_form == 'Other' and other_brand_name_from_form:
            instance.brand = other_brand_name_from_form

        if commit:
            instance.save()
            self.save_m2m()
        return instance
