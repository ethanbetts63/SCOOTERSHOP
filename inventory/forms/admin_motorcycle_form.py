from django import forms
import datetime
from inventory.models import Motorcycle, MotorcycleCondition


class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = [
            'status', 'conditions',
            'brand', 'model', 'year', 'price', 'quantity',
            'odometer', 'engine_size',
            'seats', 'transmission',
            'daily_hire_rate',
            'hourly_hire_rate',
            'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number',
            'vin_number', 'engine_number',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'brand': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'model': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'year': forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'price': forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900', 'min': '1'}),
            'odometer': forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'engine_size': forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900', 'min': '0'}),
            'seats': forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900', 'min': '0', 'max': '3'}),
            'transmission': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'daily_hire_rate': forms.NumberInput(attrs={'class': 'hire-field form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900', 'step': '0.01'}),
            'hourly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'image': forms.FileInput(attrs={'class': 'form-input mt-1 block w-full text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-l-lg file:border-0 file:text-sm file:font-semibold file:bg-gray-200 file:text-gray-700 hover:file:bg-gray-300'}),
            'rego': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'rego_exp': forms.DateInput(attrs={'type': 'date', 'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'stock_number': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'engine_number': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border border-gray-300 shadow-sm text-gray-900'}),
            'conditions': forms.CheckboxSelectMultiple(attrs={'class': 'condition-checkbox-list'}),
        }


    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        self.fields['status'].required = True
        self.fields['price'].required = False
        self.fields['daily_hire_rate'].required = False
        self.fields['hourly_hire_rate'].required = False
        self.fields['description'].required = False
        self.fields['seats'].required = False
        self.fields['transmission'].required = True
        self.fields['rego'].required = False
        self.fields['rego_exp'].required = False
        self.fields['stock_number'].required = True
        self.fields['brand'].required = True
        self.fields['model'].required = True
        self.fields['year'].required = True
        self.fields['vin_number'].required = False
        self.fields['engine_number'].required = False
        self.fields['image'].required = False
        self.fields['quantity'].required = False


    def clean(self):
        cleaned_data = super().clean()

        brand = cleaned_data.get('brand')
        model = cleaned_data.get('model')
        year = cleaned_data.get('year')
        rego = cleaned_data.get('rego')
        conditions = cleaned_data.get('conditions')
        quantity = cleaned_data.get('quantity')

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

            if is_new:
                if len(condition_names) > 1:
                    self.add_error('conditions', "A motorcycle with 'New' condition cannot have other conditions.")
                if quantity is None or quantity <= 0:
                    self.add_error('quantity', "Quantity is required and must be a positive number for 'New' motorcycles.")
            elif is_demo:
                if len(condition_names) > 1:
                    self.add_error('conditions', "A motorcycle with 'Demo' condition cannot have other conditions.")
                if quantity is None or quantity <= 0:
                    cleaned_data['quantity'] = 1

            if not is_new and (quantity is None or quantity <= 0):
                 cleaned_data['quantity'] = 1
        
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
