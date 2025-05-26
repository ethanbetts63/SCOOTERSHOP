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
        # Receive ALL add-ons, regardless of availability, for validation purposes
        all_addons_for_validation = kwargs.pop('available_addons', AddOn.objects.none()) 
        # The currently selected package instance
        self.selected_package_instance = kwargs.pop('selected_package_instance', None)
        
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = self.available_packages

        # Initialize a list to hold add-ons that should be displayed as "additional"
        self.display_addons = []

        # Determine which add-ons to display and their adjusted max_quantity
        # Only display add-ons that are available
        for addon in all_addons_for_validation: # Iterate over all addons passed
            if not addon.is_available: # Explicitly skip if not available
                continue

            is_addon_in_package = False
            if self.selected_package_instance:
                # Check if the addon is part of the selected package
                # Use .filter().exists() for efficient ManyToMany check
                is_addon_in_package = self.selected_package_instance.add_ons.filter(id=addon.id).exists()

            if is_addon_in_package:
                if addon.max_quantity > 1:
                    # If max_quantity > 1 and it's in the package, allow adding (max_quantity - 1) more
                    adjusted_max_quantity = addon.max_quantity - 1
                    if adjusted_max_quantity >= addon.min_quantity: # Ensure adjusted max is not less than min
                        self.display_addons.append({
                            'addon': addon,
                            'adjusted_max_quantity': adjusted_max_quantity,
                            'is_included_in_package': True # Flag for template/JS if needed
                        })
                # If max_quantity is 1 and it's in the package, it's completely hidden. Do nothing.
            else:
                # If not in package, display as normal with its original max_quantity
                self.display_addons.append({
                    'addon': addon,
                    'adjusted_max_quantity': addon.max_quantity,
                    'is_included_in_package': False
                })

        # Dynamically create add-on fields based on the filtered/adjusted display_addons
        for addon_info in self.display_addons:
            addon = addon_info['addon']
            adjusted_max_quantity = addon_info['adjusted_max_quantity']

            # Only create fields if the adjusted_max_quantity allows for selection (i.e., >= min_quantity)
            if adjusted_max_quantity >= addon.min_quantity:
                self.fields[f'addon_{addon.id}_selected'] = forms.BooleanField(
                    required=False,
                    label=addon.name,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'addon-checkbox',
                        'data-addon-id': str(addon.id),
                        'data-original-max-quantity': str(addon.max_quantity), # Keep original for reference if needed
                        'data-min-quantity': str(addon.min_quantity),
                        'data-adjusted-max-quantity': str(adjusted_max_quantity) # Pass adjusted max to JS
                    })
                )
                self.fields[f'addon_{addon.id}_quantity'] = forms.IntegerField(
                    min_value=addon.min_quantity,
                    max_value=adjusted_max_quantity, # Use the adjusted max_quantity here
                    initial=1, # Default to 1
                    widget=forms.NumberInput(attrs={
                        'class': 'addon-quantity',
                        'style': 'display: none;' # Hidden by default, shown by JS if selected
                    }),
                    required=False
                )

        # Store all add-ons for validation in the clean method
        self.all_addons_for_validation = {addon.id: addon for addon in all_addons_for_validation}
        print(f"DEBUG (Form __init__): self.display_addons contains: {[a['addon'].name for a in self.display_addons]}")


    def clean(self):
        cleaned_data = super().clean()
        errors = {}
        selected_package_from_form = cleaned_data.get('package') # This is the package selected by the user in the form
        selected_addons = []

        # Validate package availability (if package was selected)
        if selected_package_from_form and not selected_package_from_form.is_available:
            errors['package'] = "The selected package is no longer available."

        # Process ALL submitted add-ons, not just those in display_addons
        # Iterate over the add-ons that were actually passed during form initialization
        for addon_id, addon in self.all_addons_for_validation.items():
            is_selected = cleaned_data.get(f'addon_{addon.id}_selected')
            quantity_field_name = f'addon_{addon.id}_quantity'
            quantity = cleaned_data.get(quantity_field_name, 1) # Default to 1 if not provided

            if is_selected:
                if not addon.is_available:
                    errors.setdefault(f'addon_{addon.id}_selected', []).append(f"{addon.name} is no longer available.")
                    continue
                
                # Determine the correct adjusted_max_quantity for validation
                # This needs to be consistent with how the field was created in __init__
                # Find the addon_info for this addon in self.display_addons
                addon_info_for_validation = next((item for item in self.display_addons if item['addon'].id == addon.id), None)
                
                # If addon_info_for_validation is None, it means this addon was not meant to be displayed
                # (e.g., max_quantity=1 and included in package, or adjusted_max_quantity < min_quantity)
                # In such cases, if it was submitted, it's an invalid selection.
                if not addon_info_for_validation:
                    errors.setdefault(f'addon_{addon.id}_selected', []).append(f"{addon.name} cannot be selected as an additional item.")
                    continue

                adjusted_max_quantity_for_validation = addon_info_for_validation['adjusted_max_quantity']

                # Validate quantity against the adjusted_max_quantity
                if quantity < addon.min_quantity or quantity > adjusted_max_quantity_for_validation:
                    errors.setdefault(quantity_field_name, []).append(
                        f"Quantity for {addon.name} must be between {addon.min_quantity}-{adjusted_max_quantity_for_validation}."
                    )
                    continue
                
                selected_addons.append({
                    'addon': addon,
                    'quantity': quantity,
                    'price': addon.cost  # Capture current price
                })

        # The package/add-on exclusivity check is no longer needed here
        # because the form's __init__ already filters out add-ons that are
        # fully included in the package (max_quantity = 1) or adjusts their
        # quantity limits. The add-ons processed here are *always* "additional".

        if errors:
            for field, message in errors.items():
                if isinstance(message, list):
                    message = ' '.join(message)
                self.add_error(field, ValidationError(message))

        cleaned_data['selected_addons'] = selected_addons
        cleaned_data['selected_package'] = selected_package_from_form
        
        return cleaned_data

    def get_addon_fields(self):
        """Helper to iterate through add-on fields for the template.
        This now iterates over the pre-filtered and adjusted display_addons."""
        for addon_info in self.display_addons:
            addon = addon_info['addon']
            # Ensure the fields were actually created for this addon
            if f'addon_{addon.id}_selected' in self.fields:
                yield {
                    'addon': addon,
                    'selected_field': self[f'addon_{addon.id}_selected'],
                    'quantity_field': self[f'addon_{addon.id}_quantity']
                }
