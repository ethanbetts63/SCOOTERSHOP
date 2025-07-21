from django import forms
from ..models import SiteSettings


class BusinessInfoForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "phone_number",
            "email_address",
            "street_address",
            "address_locality",
            "address_region",
            "postal_code",
            "opening_hours_monday",
            "opening_hours_tuesday",
            "opening_hours_wednesday",
            "opening_hours_thursday",
            "opening_hours_friday",
            "opening_hours_saturday",
            "opening_hours_sunday",
            "google_places_place_id",
            "google_business_page_link",
            "youtube_link",
            "instagram_link",
            "facebook_link",
            "enable_banner",
            "banner_text",
        ]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "email_address": forms.EmailInput(attrs={"class": "form-control"}),
            "street_address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Unit 1/123 Main St",
                }
            ),
            "address_locality": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Fremantle"}
            ),
            "address_region": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., WA"}
            ),
            "postal_code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., 6160"}
            ),
            "opening_hours_monday": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9:00 AM - 5:00 PM or Closed",
                }
            ),
            "opening_hours_tuesday": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9:00 AM - 5:00 PM or Closed",
                }
            ),
            "opening_hours_wednesday": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9:00 AM - 5:00 PM or Closed",
                }
            ),
            "opening_hours_thursday": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9:00 AM - 5:00 PM or Closed",
                }
            ),
            "opening_hours_friday": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9:00 AM - 5:00 PM or Closed",
                }
            ),
            "opening_hours_saturday": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9:00 AM - 1:00 PM or Closed",
                }
            ),
            "opening_hours_sunday": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Closed"}
            ),
            "google_places_place_id": forms.TextInput(attrs={"class": "form-control"}),
            "google_business_page_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://g.page/your-business",
                }
            ),
            "youtube_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://youtube.com/your-channel",
                }
            ),
            "instagram_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://instagram.com/your-profile",
                }
            ),
            "facebook_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://facebook.com/your-page",
                }
            ),
            "enable_banner": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "banner_text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your announcement banner text here...",
                }
            ),
        }
