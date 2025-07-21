from django import forms
from dashboard.models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = [
            "author_name",
            "rating",
            "text",
            "profile_photo_url",
            "display_order",
            "is_active",
        ]
        widgets = {
            "author_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., John Doe"}
            ),
            "rating": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 5}
            ),
            "text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter the review text here...",
                }
            ),
            "profile_photo_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/photo.jpg",
                }
            ),
            "display_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        labels = {
            "author_name": "Author's Name",
            "rating": "Rating (1-5)",
            "text": "Review Text",
            "profile_photo_url": "Profile Photo URL",
            "display_order": "Display Order",
            "is_active": "Is this review active and visible?",
        }
        help_texts = {
            "display_order": "Reviews with lower numbers will be shown first.",
            "is_active": "If unchecked, this review will not be displayed on the homepage.",
            "profile_photo_url": "This is optional. If provided, it will be shown next to the review.",
        }
