from django import forms
from inventory.models import SalesTerms


class AdminSalesTermsForm(forms.ModelForm):
    class Meta:
        model = SalesTerms
        fields = [
            "content",
        ]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 20,
                    "placeholder": "Enter the full text of the terms and conditions here.",
                }
            ),
        }
        labels = {
            "content": "Terms and Conditions Content",
        }
        help_texts = {
            "content": "This text will be displayed to customers during the booking process. Saving this form will create a new, active version and archive the previous one.",
        }
