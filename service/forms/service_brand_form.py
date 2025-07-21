from django import forms
from service.models import ServiceBrand


class ServiceBrandForm(forms.ModelForm):
    class Meta:
        model = ServiceBrand
        fields = ["name", "is_accepted"]
        help_texts = {
            "name": "The name of the service brand.",
            "is_accepted": "Check this if you work on this brand.",
        }
