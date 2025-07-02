from django import forms
from service.models import ServiceType


class AdminServiceTypeForm(forms.ModelForm):

    class Meta:
        model = ServiceType
        fields = [
            "name",
            "description",
            "estimated_duration",
            "base_price",
            "is_active",
            "image",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estimated_duration": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "e.g., 3", "min": 0}
            ),
            "base_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "image": forms.FileInput(attrs={"class": "form-control-file"}),
        }
        labels = {
            "name": "Service Name",
            "description": "Service Description",
            "estimated_duration": "Estimated Duration (Days)",
            "base_price": "Base Price",
            "is_active": "Is Active?",
            "image": "Service Icon/Image",
        }
