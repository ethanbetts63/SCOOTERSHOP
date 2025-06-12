from django import forms
from django.forms import inlineformset_factory
from inventory.models import Motorcycle, MotorcycleImage


class MotorcycleImageForm(forms.ModelForm):
    class Meta:
        model = MotorcycleImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


MotorcycleImageFormSet = inlineformset_factory(
    Motorcycle,
    MotorcycleImage,
    form=MotorcycleImageForm,
    extra=1,
    can_delete=True,
    fields=['image'],
)
