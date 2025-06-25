from django import forms
from service.models import ServiceProfile

class ServiceBookingUserForm(forms.ModelForm):
    class Meta:
        model = ServiceProfile
        fields = [
            'name', 'email', 'phone_number', 'address_line_1', 
            'address_line_2', 'city', 'state', 'post_code', 'country',
        ]
        widgets = {
            'name': forms.TextInput,
            'email': forms.EmailInput,
            'phone_number': forms.TextInput,
            'address_line_1': forms.TextInput,
            'address_line_2': forms.TextInput,
            'city': forms.TextInput,
            'state': forms.TextInput,
            'post_code': forms.TextInput,
            'country': forms.TextInput,
        }
        labels = {
            'name': 'Your Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'address_line_1': 'Address Line 1',
            'address_line_2': 'Address Line 2 (Optional)',
            'city': 'City',
            'state': 'State/Province',
            'post_code': 'Post Code',
            'country': 'Country',
        }
        help_texts = {
            'name': '',
            'email': '',
            'phone_number': '',
            'address_line_1': '',
            'address_line_2': '',
            'city': '',
            'state': '',
            'post_code': '',
            'country': '',
        }
