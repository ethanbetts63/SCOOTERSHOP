from django import forms
from payments.models import RefundTerms

class AdminRefundTermsForm(forms.ModelForm):
    class Meta:
        model = RefundTerms
        fields = [
            "content",
        ]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 20,
                    "placeholder": "Enter the full text of the refund policy here.",
                }
            ),
        }
        labels = {
            "content": "Refund Policy Content",
        }
        help_texts = {
            "content": "This text will be displayed to customers. Saving this form will create a new, active version and archive the previous one.",
        }
