from django import forms
from refunds.models import RefundTerms

class AdminRefundTermsForm(forms.ModelForm):
    class Meta:
        model = RefundTerms
        fields = [
            "content",
        ]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900",
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
