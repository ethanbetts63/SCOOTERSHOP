from django import forms
import datetime
from inventory.models import Motorcycle

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
            'is_available', 'rego', 'rego_exp', 'stock_number'
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


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price'].required = False
        self.fields['daily_hire_rate'].required = False
        self.fields['hourly_hire_rate'].required = False
        self.fields['description'].required = False
        self.fields['seats'].required = False
        self.fields['transmission'].required = False
        self.fields['rego'].required = False
        self.fields['rego_exp'].required = False
        self.fields['stock_number'].required = False


    def clean(self):
        cleaned_data = super().clean()

        brand = cleaned_data.get('brand')
        model = cleaned_data.get('model')
        year = cleaned_data.get('year')
        engine_size = cleaned_data.get('engine_size')
        odometer = cleaned_data.get('odometer')
        rego = cleaned_data.get('rego')

        if brand:
            cleaned_data['brand'] = brand.capitalize()

        if model:
            cleaned_data['model'] = model.capitalize()

        if year is not None:
            current_year = datetime.date.today().year
            if year < 1885 or year > current_year + 2:
                self.add_error('year', f"Please enter a valid year between 1885 and {current_year + 2}.")

        if engine_size is not None and engine_size < 0:
            self.add_error('engine_size', "Engine size cannot be negative.")

        if odometer is not None and odometer < 0:
            self.add_error('odometer', "Odometer reading cannot be negative.")

        if rego:
            cleaned_data['rego'] = rego.upper()

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


