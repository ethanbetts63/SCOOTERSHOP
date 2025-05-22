# dashboard/forms/add_addon_form.py

from django import forms
from hire.models import AddOn # Import the AddOn model

class AddAddOnForm(forms.ModelForm):
    """
    Form for creating and updating AddOn instances.
    """
    class Meta:
        model = AddOn
        fields = ['name', 'description', 'cost', 'min_quantity', 'max_quantity', 'is_available'] # Added min_quantity and max_quantity
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}), # Added min attribute
            'max_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}), # Added min attribute
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'The name of the add-on (e.g., "Helmet", "GPS").',
            'description': 'A brief description of the add-on.',
            'cost': 'The cost of the add-on per item per day.',
            'min_quantity': 'The minimum quantity a user can select for this add-on (must be at least 1).',
            'max_quantity': 'The maximum quantity a user can select for this add-on (must be greater than or equal to min quantity).',
            'is_available': 'Check if this add-on is currently available for hire.',
        }

    def clean_cost(self):
        cost = self.cleaned_data.get('cost')
        if cost is not None and cost < 0:
            raise forms.ValidationError("Cost cannot be negative.")
        return cost

    def clean(self):
        """
        Custom validation for min_quantity and max_quantity.
        """
        cleaned_data = super().clean()
        min_quantity = cleaned_data.get('min_quantity')
        max_quantity = cleaned_data.get('max_quantity')

        if min_quantity is not None and min_quantity < 1:
            self.add_error('min_quantity', "Minimum quantity must be at least 1.")

        if min_quantity is not None and max_quantity is not None:
            if max_quantity < min_quantity:
                self.add_error('max_quantity', "Maximum quantity cannot be less than minimum quantity.")
            if max_quantity < 1: # Ensure max quantity is also at least 1
                self.add_error('max_quantity', "Maximum quantity must be at least 1.")

        return cleaned_data
