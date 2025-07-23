from django import forms
from inventory.models import Motorcycle, MotorcycleImage

class MotorcycleImageForm(forms.ModelForm):
    class Meta:
        model = MotorcycleImage
        fields = ['image']

    def __init__(self, *args, **kwargs):
        super(MotorcycleImageForm, self).__init__(*args, **kwargs)
        self.fields['image'].required = False

MotorcycleImageFormSet = forms.inlineformset_factory(
    Motorcycle,
    MotorcycleImage,
    form=MotorcycleImageForm,
    extra=0,
    can_delete=True
)