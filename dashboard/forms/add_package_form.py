from django import forms
from hire.models.hire_packages import Package # Make sure this import path is correct
from hire.models.hire_addon import AddOn # Import AddOn model

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