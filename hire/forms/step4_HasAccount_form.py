from django import forms
from ..models import DriverProfile
from django.core.exceptions import ValidationError
import datetime


class Step4HasAccountForm(forms.ModelForm):
    is_australian_resident = forms.ChoiceField(
        label="Are you an Australian resident?",
        choices=[(True, 'Yes'), (False, 'No')],
        widget=forms.Select
    )

    class Meta:
        model = DriverProfile
        fields = [
            'name',
            'email',
            'phone_number',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'post_code',
            'country',
            'date_of_birth',
            'is_australian_resident',
            'license_number',
            'license_expiry_date',
            'international_license_photo',
            'international_license_issuing_country',
            'international_license_expiry_date',
            'passport_photo',
            'passport_number',
            'passport_expiry_date',
            'id_image',
            'international_id_image',
            'license_photo',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'license_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'international_license_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'passport_expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop the 'user' and 'temp_booking' arguments as they are not directly used by ModelForm's __init__
        user = kwargs.pop('user', None)
        self.temp_booking = kwargs.pop('temp_booking', None) # Store temp_booking for validation

        # Call the parent ModelForm's __init__ method first.
        super().__init__(*args, **kwargs)

        # If no instance was provided, or if you want to ensure basic user data
        # populates fields even if no DriverProfile exists yet for the user,
        # you can keep this part.
        if user and not self.instance.pk:
            if not self.initial.get('name') and user.first_name and user.last_name:
                self.initial['name'] = f"{user.first_name} {user.last_name}".strip()
            if not self.initial.get('email') and user.email:
                self.initial['email'] = user.email

            if not self.initial.get('phone_number') and hasattr(user, 'phone_number'):
                self.initial['phone_number'] = user.phone_number
            if not self.initial.get('address_line_1') and hasattr(user, 'address_line_1'):
                self.initial['address_line_1'] = user.address_line_1
            if not self.initial.get('address_line_2') and hasattr(user, 'address_line_2'):
                self.initial['address_line_2'] = user.address_line_2
            if not self.initial.get('city') and hasattr(user, 'city'):
                self.initial['city'] = user.city
            if not self.initial.get('state') and hasattr(user, 'state'):
                self.initial['state'] = user.state
            if not self.initial.get('post_code') and hasattr(user, 'post_code'):
                self.initial['post_code'] = user.post_code
            if not self.initial.get('country') and hasattr(user, 'country'):
                self.initial['country'] = user.country


    def clean(self):
        cleaned_data = super().clean()
        is_australian_resident = cleaned_data.get('is_australian_resident')
        license_photo = cleaned_data.get('license_photo')
        international_license_photo = cleaned_data.get('international_license_photo')
        international_license_issuing_country = cleaned_data.get('international_license_issuing_country')
        international_license_expiry_date = cleaned_data.get('international_license_expiry_date')
        passport_photo = cleaned_data.get('passport_photo')
        license_number = cleaned_data.get('license_number')
        license_expiry_date = cleaned_data.get('license_expiry_date') # Get license_expiry_date
        passport_number = cleaned_data.get('passport_number')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')

        # Convert 'True'/'False' strings from ChoiceField to actual booleans
        if isinstance(is_australian_resident, str):
            is_australian_resident = (is_australian_resident.lower() == 'true')

        # Get the return date from the temporary booking
        return_date = None
        if self.temp_booking and self.temp_booking.return_date:
            return_date = self.temp_booking.return_date

        if is_australian_resident:
            if not license_photo and not self.instance.license_photo:
                self.add_error('license_photo', "Australian residents must upload their domestic driver's license photo.")
            if not license_number:
                self.add_error('license_number', "Australian residents must provide their domestic license number.")
            
            # Validate Australian license expiry date against return date
            if license_expiry_date and return_date and license_expiry_date < return_date:
                self.add_error('license_expiry_date', "Your Australian Driver's License must not expire before the end of your booking.")
        else:  # Not an Australian Resident (Foreigner)
            if not international_license_photo and not self.instance.international_license_photo:
                self.add_error('international_license_photo',
                                "Foreign drivers must upload their International Driver's License photo.")
            if not passport_photo and not self.instance.passport_photo:
                self.add_error('passport_photo', "Foreign drivers must upload their passport photo.")
            if not international_license_issuing_country:
                self.add_error('international_license_issuing_country',
                                "Foreign drivers must provide the issuing country of their International Driver's License.")
            if not international_license_expiry_date:
                self.add_error('international_license_expiry_date',
                                "Foreign drivers must provide the expiry date of their International Driver's License.")
            
            # Validate International license expiry date against return date
            if international_license_expiry_date and return_date and international_license_expiry_date < return_date:
                self.add_error('international_license_expiry_date', "Your International Driver's License must not expire before the end of your booking.")

            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
        return cleaned_data

