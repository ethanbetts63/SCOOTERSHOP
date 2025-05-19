# dashboard/forms/add_addon_form.py

from django import forms
from hire.models import AddOn # Import the AddOn model

class AddAddOnForm(forms.ModelForm):
    """
    Form for creating and updating AddOn instances.
    """
    class Meta:
        model = AddOn
        fields = ['name', 'description', 'price_type', 'cost', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price_type': forms.Select(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'The name of the add-on (e.g., "Helmet", "GPS").',
            'description': 'A brief description of the add-on.',
            'price_type': 'How the add-on is priced (e.g., per booking, per day, per item).',
            'cost': 'The cost of the add-on.',
            'is_available': 'Check if this add-on is currently available for hire.',
        }

    def clean_cost(self):
        cost = self.cleaned_data.get('cost')
        if cost is not None and cost < 0:
            raise forms.ValidationError("Cost cannot be negative.")
        return cost