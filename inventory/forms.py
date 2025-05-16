# inventory/forms.py

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
import datetime

# Import models from the inventory app
from .models import Motorcycle, MotorcycleImage, MotorcycleCondition

class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = [
            # Condition first
            'conditions',
            # Basic motorcycle details
            'brand', 'model', 'year', 'price',
            'odometer', 'engine_size',
            # Added required fields
            'seats', 'transmission',
            # Hire rates
            'daily_hire_rate', 'weekly_hire_rate', 'monthly_hire_rate',
            # Other details
            'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number'
        ]
        widgets = {
            'rego_exp': forms.DateInput(attrs={'type': 'date'}),
            'conditions': forms.CheckboxSelectMultiple(attrs={'class': 'condition-checkbox-list'}),
            'daily_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'weekly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'monthly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'seats': forms.NumberInput(attrs={'min': '1', 'max': '3'}),
            'transmission': forms.Select(attrs={'class': 'form-control'}),
        }

    engine_size = forms.IntegerField(min_value=0)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_brand(self):
        # Capitalize the brand name
        return self.cleaned_data['brand'].capitalize() if self.cleaned_data.get('brand') else None

    def clean_model(self):
        # Capitalize the model name
        return self.cleaned_data['model'].capitalize() if self.cleaned_data.get('model') else None


    def clean_rego(self):
        # Convert registration to uppercase if it exists
        if self.cleaned_data.get('rego'):
            return self.cleaned_data['rego'].upper()
        return self.cleaned_data.get('rego')

    def clean(self):
        cleaned_data = super().clean()

        # Get selected conditions (use get() with default [] for safety)
        conditions = cleaned_data.get('conditions', [])

        # Check for specific conditions by name (case-insensitive comparison)
        condition_names = [c.name.lower() for c in conditions]

        is_new = 'new' in condition_names
        is_used = 'used' in condition_names
        is_demo = 'demo' in condition_names
        is_hire = 'hire' in condition_names

        # If hire condition is selected, daily_hire_rate is required
        if is_hire and not cleaned_data.get('daily_hire_rate'):
            self.add_error('daily_hire_rate', 'Daily hire rate is required for hire motorcycles')

        # If new, used, or demo condition is selected, price is required
        if (is_new or is_used or is_demo) and not cleaned_data.get('price'):
            self.add_error('price', 'Price is required for motorcycles listed as New, Used, or Demo')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.year and instance.brand and instance.model:
             instance.title = f"{instance.year} {instance.brand} {instance.model}"
        elif instance.brand and instance.model:
             instance.title = f"{instance.brand} {instance.model}"
        else:
             instance.title = "Untitled Motorcycle" 
        if commit:
            instance.save()
            self.save_m2m() 
        return instance

class MotorcycleImageForm(forms.ModelForm):
    class Meta:
        model = MotorcycleImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            # 'multiple': True # This attribute belongs on the input element, often handled by frontend or custom widget
        }

# Create a formset for multiple images
MotorcycleImageFormSet = inlineformset_factory(
    Motorcycle, MotorcycleImage,
    form=MotorcycleImageForm,
    extra=1,  # Start with 1 empty form for adding a new image
    can_delete=True,  # Allow deleting existing images
    fields=['image'],
)