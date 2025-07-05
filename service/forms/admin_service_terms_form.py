from django import forms
from service.models import ServiceTerms 
class AdminServiceTermsForm(forms.ModelForm):
    """
    Form for creating and updating ServiceTerms instances in the admin interface.
    """
    class Meta:
        model = ServiceTerms
        fields = [
            "content",
        ]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 20,
                    "placeholder": "Enter the full text of the service terms here.",
                }
            ),
        }
        labels = {
            "content": "Service Terms Content",
        }
        help_texts = {
            "content": "This text will be displayed to customers. Saving this form will create a new, active version and archive the previous one.",
        }
