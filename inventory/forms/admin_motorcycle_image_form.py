from django import forms
from django.forms import inlineformset_factory
from inventory.models import Motorcycle, MotorcycleImage

from django import forms
from django.forms import inlineformset_factory
from inventory.models import Motorcycle, MotorcycleImage


class MotorcycleImageForm(forms.ModelForm):

    class Meta:
        model = MotorcycleImage
        fields = [
            "image",
        ]
        widgets = {
            "image": forms.FileInput(
                attrs={"class": "form-input mt-1 block w-full text-gray-900"}
            )
        }


MotorcycleImageFormSet = inlineformset_factory(
    Motorcycle,
    MotorcycleImage,
    form=MotorcycleImageForm,
    extra=0,
    can_delete=True,
)
