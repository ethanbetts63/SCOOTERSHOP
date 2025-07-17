from django import forms
from inventory.models import Salesfaq


class AdminSalesfaqForm(forms.ModelForm):
    class Meta:
        model = Salesfaq
        fields = [
            "booking_step",
            "question",
            "answer",
            "display_order",
            "is_active",
        ]
        widgets = {
            "booking_step": forms.Select(attrs={"class": "form-control"}),
            "question": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., How much is the deposit?",
                }
            ),
            "answer": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Provide a clear and concise answer.",
                }
            ),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        labels = {
            "booking_step": "Associated Booking Step",
            "question": "Question",
            "answer": "Answer",
            "display_order": "Display Order",
            "is_active": "Is this faq active and visible?",
        }
        help_texts = {
            "display_order": "faqs with lower numbers will be shown first.",
            "is_active": "If unchecked, this faq will not be displayed anywhere on the site.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["answer"].label_attrs = {"class": "align-top"}
