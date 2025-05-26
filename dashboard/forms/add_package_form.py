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
        fields = ['name', 'description', 'add_ons', 'hourly_cost', 'daily_cost', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            # Added widgets for hourly_cost and daily_cost
            'hourly_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'daily_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        help_texts = {
            'name': 'A unique name for the package (e.g., "Weekend Warrior Pack").',
            # Updated help texts for hourly_cost and daily_cost
            'hourly_cost': 'The total price for this package bundle per hour (e.g., 9.99).',
            'daily_cost': 'The total price for this package bundle per day (e.g., 99.99).',
            'is_available': 'Check if this package should be available for customers to book.',
        }

    # Custom clean methods for new hourly_cost and daily_cost fields
    def clean_hourly_cost(self):
        hourly_cost = self.cleaned_data.get('hourly_cost')
        if hourly_cost is not None and hourly_cost < 0:
            raise forms.ValidationError("Package hourly cost cannot be negative.")
        return hourly_cost

    def clean_daily_cost(self):
        daily_cost = self.cleaned_data.get('daily_cost')
        if daily_cost is not None and daily_cost < 0:
            raise forms.ValidationError("Package daily cost cannot be negative.")
        return daily_cost

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
