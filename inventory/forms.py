                    

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
import datetime

                                      
from .models import Motorcycle, MotorcycleImage, MotorcycleCondition

class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = [
                             
            'conditions',
                                      
            'brand', 'model', 'year', 'price',
            'odometer', 'engine_size',
                                                                                 
            'seats', 'transmission',
            'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number'
        ]
        widgets = {
            'rego_exp': forms.DateInput(attrs={'type': 'date'}),
            'conditions': forms.CheckboxSelectMultiple(attrs={'class': 'condition-checkbox-list'}),                                                                            
            'seats': forms.NumberInput(attrs={'min': '0', 'max': '3'}),                                           
            'transmission': forms.Select(attrs={'class': 'form-control'}),
        }

                                                                  
    engine_size = forms.IntegerField(min_value=0)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
                                                                       
        self.fields['price'].required = False
        self.fields['description'].required = False
        self.fields['seats'].required = False
        self.fields['transmission'].required = False
                                                                                                   


    def clean_brand(self):
                                                            
        brand = self.cleaned_data.get('brand')
        if not brand:
             raise forms.ValidationError("Brand is required.")
        return brand.capitalize()

    def clean_model(self):
                                                            
        model = self.cleaned_data.get('model')
        if not model:
             raise forms.ValidationError("Model is required.")
        return model.capitalize()

    def clean_year(self):
                               
        year = self.cleaned_data.get('year')
        if not year:
             raise forms.ValidationError("Year is required.")
                                                              
        current_year = datetime.date.today().year
        if year < 1885 or year > current_year + 2:                                                      
             raise forms.ValidationError(f"Please enter a valid year between 1885 and {current_year + 2}.")
        return year

    def clean_engine_size(self):
                                       
         engine_size = self.cleaned_data.get('engine_size')
         if engine_size is None:                               
             raise forms.ValidationError("Engine size is required.")
         if engine_size < 0:
              raise forms.ValidationError("Engine size cannot be negative.")
         return engine_size

    def clean_odometer(self):
                                                                                  
        odometer = self.cleaned_data.get('odometer')
                                                                                           
                                                                                        
                                                  
        if odometer is not None and odometer < 0:
            raise forms.ValidationError("Odometer reading cannot be negative.")
        return odometer


    def clean_rego(self):
                                                        
        if self.cleaned_data.get('rego'):
            return self.cleaned_data['rego'].upper()
        return self.cleaned_data.get('rego')

                                                    
    def clean(self):
        cleaned_data = super().clean()                                 
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

class MotorcycleImageForm(forms.ModelForm):
    class Meta:
        model = MotorcycleImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
                                                                                                                        
        }

                                      
MotorcycleImageFormSet = inlineformset_factory(
    Motorcycle, MotorcycleImage,
    form=MotorcycleImageForm,
    extra=1,                                                  
    can_delete=True,                                  
    fields=['image'],
)
