# dashboard/forms/add_package_form.py
from django import forms
from hire.models.hire_packages import Package
from hire.models.hire_addon import AddOn

class AddPackageForm(forms.ModelForm):
    add_ons = forms.ModelMultipleChoiceField(
        queryset=AddOn.objects.filter(is_available=True).order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select individual add-ons to include in this package."
    )

    class Meta:
        model = Package
        fields = ['name', 'description', 'add_ons', 'package_price', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'name': 'A unique name for the package (e.g., "Weekend Warrior Pack").',
            'package_price': 'The total price for this package bundle (e.g., 99.99).',
            'is_available': 'Check if this package should be available for customers to book.',
        }

    def clean_package_price(self):
        package_price = self.cleaned_data.get('package_price')
        if package_price is not None and package_price < 0:
            raise forms.ValidationError("Package price cannot be negative.")
        return package_price

    def clean_add_ons(self):
        # This clean method will be called after individual field clean methods,
        # but before the model's clean method.
        # It's suitable for validating ManyToMany fields.
        selected_addons = self.cleaned_data.get('add_ons')
        if selected_addons:
            unavailable_addons = [addon.name for addon in selected_addons if not addon.is_available]
            if unavailable_addons:
                raise forms.ValidationError(
                    f"The following add-ons selected are not available: {', '.join(unavailable_addons)}"
                )
        return selected_addons