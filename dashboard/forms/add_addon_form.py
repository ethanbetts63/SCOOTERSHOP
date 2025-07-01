                                   

from django import forms
from hire.models import AddOn                         

class AddAddOnForm(forms.ModelForm):
    """
    Form for creating and updating AddOn instances.
    """
    class Meta:
        model = AddOn
                                                          
        fields = ['name', 'description', 'hourly_cost', 'daily_cost', 'min_quantity', 'max_quantity', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                                                            
            'hourly_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'daily_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'The name of the add-on (e.g., "Helmet", "GPS").',
            'description': 'A brief description of the add-on.',
                                                               
            'hourly_cost': 'The cost of the add-on per item per hour.',
            'daily_cost': 'The cost of the add-on per item per day.',
            'min_quantity': 'The minimum quantity a user can select for this add-on (must be at least 1).',
            'max_quantity': 'The maximum quantity a user can select for this add-on (must be greater than or equal to min quantity).',
            'is_available': 'Check if this add-on is currently available for hire.',
        }

                                                                    
    def clean_hourly_cost(self):
        hourly_cost = self.cleaned_data.get('hourly_cost')
        if hourly_cost is not None and hourly_cost < 0:
            raise forms.ValidationError("Hourly cost cannot be negative.")
        return hourly_cost

    def clean_daily_cost(self):
        daily_cost = self.cleaned_data.get('daily_cost')
        if daily_cost is not None and daily_cost < 0:
            raise forms.ValidationError("Daily cost cannot be negative.")
        return daily_cost

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
            if max_quantity < 1:                                         
                self.add_error('max_quantity', "Maximum quantity must be at least 1.")

        return cleaned_data
