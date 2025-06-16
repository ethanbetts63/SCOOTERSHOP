from django import forms
from ..models import DriverProfile
from django.core.exceptions import ValidationError
import datetime


class Step4NoAccountForm(forms.ModelForm):
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
            'license_photo',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'license_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'international_license_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'passport_expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.temp_booking = kwargs.pop('temp_booking', None)
        super().__init__(*args, **kwargs)


    def clean(self):
        cleaned_data = super().clean()

        is_australian_resident_str = cleaned_data.get('is_australian_resident')

        if isinstance(is_australian_resident_str, str):
            is_australian_resident = (is_australian_resident_str.lower() == 'true')
            cleaned_data['is_australian_resident'] = is_australian_resident
        else:
            is_australian_resident = is_australian_resident_str

        license_photo = cleaned_data.get('license_photo')
        international_license_photo = cleaned_data.get('international_license_photo')
        international_license_issuing_country = cleaned_data.get('international_license_issuing_country')
        international_license_expiry_date = cleaned_data.get('international_license_expiry_date')
        passport_photo = cleaned_data.get('passport_photo')
        license_number = cleaned_data.get('license_number')
        license_expiry_date = cleaned_data.get('license_expiry_date')
        passport_number = cleaned_data.get('passport_number')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')

        return_date = None
        if self.temp_booking and self.temp_booking.return_date:
            return_date = self.temp_booking.return_date

        if is_australian_resident:
            if not license_photo and not (self.instance and self.instance.license_photo):
                self.add_error('license_photo', "Australian residents must upload their domestic driver's license photo.")
            if not license_number:
                self.add_error('license_number', "Australian residents must provide their domestic license number.")
            if not license_expiry_date:
                self.add_error('license_expiry_date', "Australian residents must provide their domestic license expiry date.")
            elif return_date and license_expiry_date and license_expiry_date < return_date:
                self.add_error('license_expiry_date', "Your Australian Driver's License must not expire before the end of your booking.")
            
        else:
            if not international_license_photo and not (self.instance and self.instance.international_license_photo):
                self.add_error('international_license_photo',
                                 "Foreign drivers must upload their International Driver's License photo.")
            if not international_license_issuing_country:
                self.add_error('international_license_issuing_country',
                                 "Foreign drivers must provide the issuing country of their International Driver's License.")
            if not international_license_expiry_date:
                self.add_error('international_license_expiry_date',
                                 "Foreign drivers must provide the expiry date of their International Driver's License.")
            elif return_date and international_license_expiry_date and international_license_expiry_date < return_date:
                self.add_error('international_license_expiry_date', "Your International Driver's License must not expire before the end of your booking.")
            
            if not passport_photo and not (self.instance and self.instance.passport_photo):
                self.add_error('passport_photo', "Foreign drivers must upload their passport photo.")
            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
            elif return_date and passport_expiry_date and passport_expiry_date < return_date:
                self.add_error('passport_expiry_date', "Your passport must not expire before the end of your booking.")
            
        return cleaned_data
