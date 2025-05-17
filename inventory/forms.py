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
            # Added required fields (now some are optional, odometer is required)
            'seats', 'transmission',
            # Hire rates
            'daily_hire_rate', 'weekly_hire_rate', 'monthly_hire_rate',
            'hourly_hire_rate',
            # Other details
            'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number'
        ]
        widgets = {
            'hourly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),

            'rego_exp': forms.DateInput(attrs={'type': 'date'}),
            'conditions': forms.CheckboxSelectMultiple(attrs={'class': 'condition-checkbox-list'}),
            'daily_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'weekly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'monthly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            # Seats widget remains, but field is no longer required by model
            'seats': forms.NumberInput(attrs={'min': '0', 'max': '3'}), # Changed min to 0 since seats can be None
            'transmission': forms.Select(attrs={'class': 'form-control'}),
        }

    # Engine size remains required as it wasn't listed for removal
    engine_size = forms.IntegerField(min_value=0)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark fields that are now optional as not required in the form
        self.fields['price'].required = False
        self.fields['daily_hire_rate'].required = False
        self.fields['weekly_hire_rate'].required = False
        self.fields['monthly_hire_rate'].required = False
        self.fields['hourly_hire_rate'].required = False
        self.fields['description'].required = False
        self.fields['seats'].required = False
        self.fields['transmission'].required = False
        # Removed: self.fields['odometer'].required = False # Odometer is now required by the model


    def clean_brand(self):
        # Capitalize the brand name - Brand remains required
        brand = self.cleaned_data.get('brand')
        if not brand:
             raise forms.ValidationError("Brand is required.")
        return brand.capitalize()

    def clean_model(self):
        # Capitalize the model name - Model remains required
        model = self.cleaned_data.get('model')
        if not model:
             raise forms.ValidationError("Model is required.")
        return model.capitalize()

    def clean_year(self):
        # Year remains required
        year = self.cleaned_data.get('year')
        if not year:
             raise forms.ValidationError("Year is required.")
        # Optional: Add validation for a reasonable year range
        current_year = datetime.date.today().year
        if year < 1885 or year > current_year + 2: # Motorcycles invented ~1885, allow for future models
             raise forms.ValidationError(f"Please enter a valid year between 1885 and {current_year + 2}.")
        return year

    def clean_engine_size(self):
         # Engine Size remains required
         engine_size = self.cleaned_data.get('engine_size')
         if engine_size is None: # Use is None for IntegerField
             raise forms.ValidationError("Engine size is required.")
         if engine_size < 0:
              raise forms.ValidationError("Engine size cannot be negative.")
         return engine_size

    def clean_odometer(self):
        # Odometer is now required by the model. Add specific validation if needed
        odometer = self.cleaned_data.get('odometer')
        # The model field is an IntegerField without null=True, so Django's form validation
        # will handle the "required" check. We can add custom validation here if needed,
        # for example, ensuring it's not negative.
        if odometer is not None and odometer < 0:
            raise forms.ValidationError("Odometer reading cannot be negative.")
        return odometer


    def clean_rego(self):
        # Convert registration to uppercase if it exists
        if self.cleaned_data.get('rego'):
            return self.cleaned_data['rego'].upper()
        return self.cleaned_data.get('rego')

    # Removed the custom price and daily_hire_rate validation from clean method

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Ensure title is generated even if some fields are optional
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