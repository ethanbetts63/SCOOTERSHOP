from django import forms
from ..models import SiteSettings

class VisibilitySettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'enable_hire',
            'enable_service_booking',
            'enable_user_accounts',
            'enable_contact_page',
            'enable_about_page',
            'enable_map_display',
            'enable_featured_section',
            'enable_privacy_policy_page',
            'enable_returns_page',
            'enable_security_page',
            'enable_terms_page',
            'enable_google_places_reviews',
        ]
        widgets = {
            'enable_hire': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_service_booking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_user_accounts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_contact_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_about_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_map_display': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_featured_section': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_privacy_policy_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_returns_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_security_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_terms_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_google_places_reviews': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }