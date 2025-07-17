from django import forms
from ..models import SiteSettings


class VisibilitySettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "enable_sales_new",
            "enable_sales_used",
            "enable_service_booking",
            "enable_user_accounts",
            "enable_contact_page",
            "enable_map_display",
            "enable_privacy_policy_page",
            "enable_returns_page",
            "enable_security_page",
            "enable_refunds",
            "enable_google_places_reviews",
            "display_phone_number",
            "display_address",
            "display_opening_hours",
            "enable_faq_service",
            "enable_faq_sales",
            "enable_motorcycle_mover",
        ]
        widgets = {
            "enable_sales_new": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_sales_used": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_service_booking": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_user_accounts": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_contact_page": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_map_display": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_privacy_policy_page": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_returns_page": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_security_page": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_refunds": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "enable_google_places_reviews": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "display_phone_number": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "display_address": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "display_opening_hours": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_faq_service": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_faq_sales": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_motorcycle_mover": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
