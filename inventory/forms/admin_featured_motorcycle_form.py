from django import forms
from inventory.models import FeaturedMotorcycle

class FeaturedMotorcycleForm(forms.ModelForm):
    class Meta:
        model = FeaturedMotorcycle
        fields = ['motorcycle', 'category', 'order']
