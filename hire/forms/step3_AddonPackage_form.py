from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, RadioSelect
from ..models import AddOn, Package
from hire.hire_pricing import calculate_addon_price

class Step3AddOnsPackagesForm(forms.Form):
    package = ModelChoiceField(
        queryset=Package.objects.none(),
        widget=RadioSelect(attrs={'class': 'package-radio'}),
        required=False,
        label="Select a Package"
    )

    def __init__(self, *args, **kwargs):
        self.available_packages = kwargs.pop('available_packages', Package.objects.none())
        self.all_addons_for_validation = kwargs.pop('available_addons', AddOn.objects.none())
        self.selected_package_instance = kwargs.pop('selected_package_instance', None)
        self.temp_booking = kwargs.pop('temp_booking', None)
        self.hire_settings = kwargs.pop('hire_settings', None)
        
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = self.available_packages
        self.fields['package'].label_from_instance = lambda obj: f"{obj.name} (Daily: {obj.daily_cost:.2f}, Hourly: {obj.hourly_cost:.2f})"


        self.display_addons = []

        for addon in self.all_addons_for_validation:
            if not addon.is_available:
                continue

            is_addon_in_package = False
            if self.selected_package_instance:
                is_addon_in_package = self.selected_package_instance.add_ons.filter(id=addon.id).exists()

            if is_addon_in_package:
                if addon.max_quantity > 1:
                    adjusted_max_quantity = addon.max_quantity - 1
                    if adjusted_max_quantity >= addon.min_quantity:
                        self.display_addons.append({
                            'addon': addon,
                            'adjusted_max_quantity': adjusted_max_quantity,
                            'is_included_in_package': True
                        })
            else:
                self.display_addons.append({
                    'addon': addon,
                    'adjusted_max_quantity': addon.max_quantity,
                    'is_included_in_package': False
                })

        for addon_info in self.display_addons:
            addon = addon_info['addon']
            adjusted_max_quantity = addon_info['adjusted_max_quantity']

            if adjusted_max_quantity >= addon.min_quantity:
                self.fields[f'addon_{addon.id}_selected'] = forms.BooleanField(
                    required=False,
                    label=addon.name,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'addon-checkbox',
                        'data-addon-id': str(addon.id),
                        'data-original-max-quantity': str(addon.max_quantity),
                        'data-min-quantity': str(addon.min_quantity),
                        'data-adjusted-max-quantity': str(adjusted_max_quantity)
                    })
                )
                self.fields[f'addon_{addon.id}_quantity'] = forms.IntegerField(
                    min_value=addon.min_quantity,
                    max_value=adjusted_max_quantity,
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
        selected_package_from_form = cleaned_data.get('package')
        selected_addons = []

        if selected_package_from_form and not selected_package_from_form.is_available:
            errors['package'] = "The selected package is no longer available."

        pickup_date = self.temp_booking.pickup_date if self.temp_booking else None
        pickup_time = self.temp_booking.pickup_time if self.temp_booking else None
        return_date = self.temp_booking.return_date if self.temp_booking else None
        return_time = self.temp_booking.return_time if self.temp_booking else None


        for addon_id, addon in self.all_addons_for_validation.items():
            is_selected = cleaned_data.get(f'addon_{addon.id}_selected')
            quantity_field_name = f'addon_{addon.id}_quantity'
            quantity = cleaned_data.get(quantity_field_name, 1)

            if is_selected:
                if not addon.is_available:
                    errors.setdefault(f'addon_{addon.id}_selected', []).append(f"{addon.name} is no longer available.")
                    continue
                
                addon_info_for_validation = next((item for item in self.display_addons if item['addon'].id == addon.id), None)
                
                if not addon_info_for_validation:
                    errors.setdefault(f'addon_{addon.id}_selected', []).append(f"{addon.name} cannot be selected as an additional item.")
                    continue

                adjusted_max_quantity_for_validation = addon_info_for_validation['adjusted_max_quantity']

                if quantity < addon.min_quantity or quantity > adjusted_max_quantity_for_validation:
                    errors.setdefault(quantity_field_name, []).append(
                        f"Quantity for {addon.name} must be between {addon.min_quantity}-{adjusted_max_quantity_for_validation}."
                    )
                    continue
                
                if all([addon, quantity, pickup_date, return_date, pickup_time, return_time, self.hire_settings]):
                    calculated_addon_price = calculate_addon_price(
                        addon_instance=addon,
                        quantity=quantity,
                        pickup_date=pickup_date,
                        return_date=return_date,
                        pickup_time=pickup_time,
                        return_time=return_time,
                        hire_settings=self.hire_settings
                    )
                    selected_addons.append({
                        'addon': addon,
                        'quantity': quantity,
                        'price': calculated_addon_price
                    })
                else:
                    errors.setdefault(f'addon_{addon.id}_selected', []).append("Cannot calculate add-on price due to missing booking details or hire settings.")


        if errors:
            for field, message in errors.items():
                if isinstance(message, list):
                    message = ' '.join(message)
                self.add_error(field, ValidationError(message))

        cleaned_data['selected_addons'] = selected_addons
        cleaned_data['selected_package'] = selected_package_from_form
        
        return cleaned_data

    def get_addon_fields(self):
        for addon_info in self.display_addons:
            addon = addon_info['addon']
            if f'addon_{addon.id}_selected' in self.fields:
                yield {
                    'addon': addon,
                    'selected_field': self[f'addon_{addon.id}_selected'],
                    'quantity_field': self[f'addon_{addon.id}_quantity']
                }
