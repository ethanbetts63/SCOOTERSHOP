from django import forms
from inventory.models import SalesTerms

class AdminSalesTermsForm(forms.ModelForm):

    class Meta:
        model = SalesTerms
        fields = [
            "content",
            "is_active",
        ]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 20,
                    "placeholder": "Enter the full text of the terms and conditions here.",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        labels = {
            "content": "Terms and Conditions Content",
            "is_active": "Set this version as active?",
        }
        help_texts = {
            "content": "This text will be displayed to customers during the booking process.",
            "is_active": "Only one version can be active at a time. Activating this one will deactivate the previous active version.",
        }

