from django import forms
from inventory.models import FeaturedMotorcycle, Motorcycle

class FeaturedMotorcycleForm(forms.ModelForm):
    class Meta:
        model = FeaturedMotorcycle
        fields = ['motorcycle', 'category', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.category == 'new':
                self.fields['motorcycle'].queryset = Motorcycle.objects.filter(condition='new')
            elif self.instance.category == 'used':
                self.fields['motorcycle'].queryset = Motorcycle.objects.filter(condition='used')
        else:
            category = self.initial.get('category')
            if category == 'new':
                self.fields['motorcycle'].queryset = Motorcycle.objects.filter(condition='new')
            elif category == 'used':
                self.fields['motorcycle'].queryset = Motorcycle.objects.filter(condition='used')
