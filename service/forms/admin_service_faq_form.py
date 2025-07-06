from django import forms
from service.models import Servicefaq


class AdminServicefaqForm(forms.ModelForm):

    class Meta:
        model = Servicefaq
        fields = [
            "booking_step",
            "question",
            "answer",
            "display_order",
            "is_active",
        ]
        widgets = {
            "booking_step": forms.Select(
                attrs={
                    "class": "form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                }
            ),
            "question": forms.TextInput(
                attrs={
                    "class": "form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500",
                    "placeholder": "e.g., How long will the service take?",
                }
            ),
            "answer": forms.Textarea(
                attrs={
                    "class": "form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500",
                    "rows": 5,
                    "placeholder": "Provide a clear and concise answer.",
                }
            ),
            "display_order": forms.NumberInput(
                attrs={
                    "class": "form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-checkbox h-5 w-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                }
            ),
        }
        labels = {
            "booking_step": "Associated Service Step",
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
