from django import forms
import datetime
from inventory.models import Motorcycle, MotorcycleCondition # Ensure MotorcycleCondition is imported if used in clean method

class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = [
            'conditions',
            'brand', 'model', 'year', 'price',
            'odometer', 'engine_size',
            'seats', 'transmission',
            'daily_hire_rate',
            'hourly_hire_rate',
            'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number',
            'vin_number', 'engine_number', # Added these fields
        ]
        widgets = {
            'hourly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'rego_exp': forms.DateInput(attrs={'type': 'date'}),
            'conditions': forms.CheckboxSelectMultiple(attrs={'class': 'condition-checkbox-list'}),
            'daily_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'seats': forms.NumberInput(attrs={'min': '0', 'max': '3'}),
            'transmission': forms.Select(attrs={'class': 'form-control'}),
        }

    engine_size = forms.IntegerField(min_value=0)
    odometer = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price'].required = False
        self.fields['daily_hire_rate'].required = False
        self.fields['hourly_hire_rate'].required = False
        self.fields['description'].required = False
        self.fields['seats'].required = False
        self.fields['transmission'].required = True # User specified
        self.fields['rego'].required = False
        self.fields['rego_exp'].required = False
        self.fields['stock_number'].required = True # User specified
        self.fields['brand'].required = True # User specified
        self.fields['model'].required = True # User specified
        self.fields['year'].required = True # User specified
        self.fields['vin_number'].required = False # Made optional
        self.fields['engine_number'].required = False # Made optional


    def clean(self):
        cleaned_data = super().clean()

        brand = cleaned_data.get('brand')
        model = cleaned_data.get('model')
        year = cleaned_data.get('year')
        rego = cleaned_data.get('rego')
        conditions = cleaned_data.get('conditions') # Get selected conditions

        if brand:
            cleaned_data['brand'] = brand.capitalize()

        if model:
            cleaned_data['model'] = model.capitalize()

        if year is not None:
            current_year = datetime.date.today().year
            if year < 1885 or year > current_year + 2:
                self.add_error('year', f"Please enter a valid year between 1885 and {current_year + 2}.")

        if rego:
            cleaned_data['rego'] = rego.upper()

        if conditions:
            condition_names = [c.name for c in conditions]
            is_new = 'new' in condition_names
            is_demo = 'demo' in condition_names

            if is_new and len(condition_names) > 1:
                self.add_error('conditions', "A motorcycle with 'New' condition cannot have other conditions.")
            if is_demo and len(condition_names) > 1:
                self.add_error('conditions', "A motorcycle with 'Demo' condition cannot have other conditions.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        parts = []
        if instance.year:
            parts.append(str(instance.year))
        if instance.brand:
            parts.append(instance.brand)
        if instance.model:
            parts.append(instance.model)

        if parts:
            instance.title = " ".join(parts)
        else:
            instance.title = "Untitled Motorcycle"

        if commit:
            instance.save()
            self.save_m2m()
        return instance
