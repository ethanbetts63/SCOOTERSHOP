# hire/forms/step3_add_ons_packages_form.py
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, RadioSelect
from ..models import AddOn, Package

class Step3AddOnsPackagesForm(forms.Form):
    package = ModelChoiceField(
        queryset=Package.objects.none(),  # Set dynamically in __init__
        widget=RadioSelect(attrs={'class': 'package-radio'}),
        required=False,
        label="Select a Package"
    )

    def __init__(self, *args, **kwargs):
        self.available_packages = kwargs.pop('available_packages', Package.objects.none())
        self.available_addons = kwargs.pop('available_addons', AddOn.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = self.available_packages

        # Dynamically create add-on fields
        for addon in self.available_addons:
            self.fields[f'addon_{addon.id}_selected'] = forms.BooleanField(
                required=False,
                label=addon.name,
                widget=forms.CheckboxInput(attrs={
                    'class': 'addon-checkbox',
                    'data-addon-id': str(addon.id)
                })
            )
            self.fields[f'addon_{addon.id}_quantity'] = forms.IntegerField(
                min_value=1,
                max_value=10,
                initial=1,
                widget=forms.NumberInput(attrs={
                    'class': 'addon-quantity',
                    'style': 'display: none;'
                }),
                required=False
            )

    def clean(self):
        cleaned_data = super().clean()
        errors = {}
        selected_package = cleaned_data.get('package')
        selected_addons = []

        # Validate package availability
        if selected_package and not selected_package.is_available:
            errors['package'] = "The selected package is no longer available."

        # Process add-ons
        for addon in self.available_addons:
            is_selected = cleaned_data.get(f'addon_{addon.id}_selected')
            quantity = cleaned_data.get(f'addon_{addon.id}_quantity', 1)

            if is_selected:
                # Validate add-on availability
                if not addon.is_available:
                    errors[f'addon_{addon.id}_selected'] = f"{addon.name} is no longer available."
                    continue
                
                # Validate quantity
                if quantity < 1 or quantity > 10:
                    errors[f'addon_{addon.id}_quantity'] = "Quantity must be between 1-10."
                    continue
                
                selected_addons.append({
                    'addon': addon,
                    'quantity': quantity,
                    'price': addon.cost  # Capture current price
                })

        # Validate package/add-on exclusivity
        if selected_package:
            package_addons = selected_package.add_ons.all()
            for pa in package_addons:
                if any(a['addon'] == pa for a in selected_addons):
                    errors.setdefault('package', []).append(
                        f"{pa.name} is already included in the package"
                    )

        if errors:
            for field, message in errors.items():
                if isinstance(message, list):
                    message = ' '.join(message)
                self.add_error(field, ValidationError(message))

        # Add processed data to cleaned_data
        cleaned_data['selected_addons'] = selected_addons
        cleaned_data['selected_package'] = selected_package
        
        return cleaned_data

    def get_addon_fields(self):
        """Helper to iterate through add-on fields in template"""
        for addon in self.available_addons:
            yield {
                'addon': addon,
                'selected_field': self[f'addon_{addon.id}_selected'],
                'quantity_field': self[f'addon_{addon.id}_quantity']
            }