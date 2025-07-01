from django import forms
from ..models import SiteSettings

class BusinessInfoForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
                                 
            'phone_number', 'email_address', 'storefront_address',

                            
            'opening_hours_monday', 'opening_hours_tuesday', 'opening_hours_wednesday',
            'opening_hours_thursday', 'opening_hours_friday', 'opening_hours_saturday',
            'opening_hours_sunday',
                                                       
            'google_places_place_id',
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email_address': forms.EmailInput(attrs={'class': 'form-control'}),
            'storefront_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            'opening_hours_monday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_tuesday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_wednesday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_thursday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_friday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_saturday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 1:00 PM or Closed'}),
            'opening_hours_sunday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Closed'}),
                                                                 
            'google_places_place_id': forms.TextInput(attrs={'class': 'form-control'}),
        }