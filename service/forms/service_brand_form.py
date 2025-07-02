from django import forms
from service.models import ServiceBrand


class ServiceBrandForm(forms.ModelForm):
    class Meta:
        model = ServiceBrand
        fields = ["name", "image"]
        help_texts = {
            "name": "The name of the service brand.",
            "image": "Upload an optional image for this brand.",
        }
