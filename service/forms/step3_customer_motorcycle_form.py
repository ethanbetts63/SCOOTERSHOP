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
        brand_choices = [(name, name) for name in brand_names]
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

        # Removed the 'ordered_fields' logic and 'is_required_field' custom attribute
        # as fields are now explicitly ordered in the HTML template.


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
        ]
        widgets = {
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'engine_size': forms.TextInput(attrs={'class': 'form-control'}),
            'rego': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control'}),
            'odometer': forms.NumberInput(attrs={'class': 'form-control'}),
            'transmission': forms.Select(attrs={'class': 'form-control'}), # Changed to Select for choices
            'engine_number': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            'make': _('Make'),
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

        if brand == 'Other' and not other_brand_name:
            self.add_error('other_brand_name', _("Please specify the brand name when 'Other' is selected."))
        elif brand != 'Other' and other_brand_name:
            # If a specific brand is chosen, clear other_brand_name
            cleaned_data['other_brand_name'] = ''

        return cleaned_data

    def save(self, commit=True):
        brand_from_form = self.cleaned_data['brand']
        other_brand_name_from_form = self.cleaned_data.get('other_brand_name')

        instance = super().save(commit=False)

        if brand_from_form == 'Other' and other_brand_name_from_form:
            instance.brand = other_brand_name_from_form
        # If a specific brand was chosen, instance.brand is already correctly set
        # from the 'brand' field in Meta.fields (via the ChoiceField's value).
        # No else needed, as instance.brand holds the selected value if not 'Other'.

        if commit:
            instance.save()
            self.save_m2m()
        return instance
