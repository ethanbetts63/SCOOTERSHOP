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
            # Set min_value and max_value from the AddOn model instance
            self.fields[f'addon_{addon.id}_quantity'] = forms.IntegerField(
                min_value=addon.min_quantity, # Use addon's min_quantity
                max_value=addon.max_quantity, # Use addon's max_quantity
                initial=1, # Default to 1
                widget=forms.NumberInput(attrs={
                    'class': 'addon-quantity',
                    'style': 'display: none;' # Hidden by default, shown by JS if selected
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
            # Get the quantity field dynamically
            quantity_field_name = f'addon_{addon.id}_quantity'
            quantity = cleaned_data.get(quantity_field_name, 1) # Default to 1 if not provided

            if is_selected:
                # Validate add-on availability
                if not addon.is_available:
                    errors[f'addon_{addon.id}_selected'] = f"{addon.name} is no longer available."
                    continue
                
                # Validate quantity using addon's min_quantity and max_quantity
                if quantity < addon.min_quantity or quantity > addon.max_quantity:
                    errors[quantity_field_name] = f"Quantity for {addon.name} must be between {addon.min_quantity}-{addon.max_quantity}."
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
