# hire/forms/step4_NoAccount_form.py
from django import forms
from ..models import DriverProfile
from django.core.exceptions import ValidationError

class Step4NoAccountForm(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ['name', 'email', 'phone', 'address', 'city', 'county', 'postcode', 'date_of_birth',
                  'is_australian_resident', 'license_number', 'license_issuing_country', 'license_expiry_date',
                  'license_photo', 'international_license_photo', 'passport_photo', 'passport_number',
                  'passport_expiry_date']

    def clean(self):
        cleaned_data = super().clean()
        is_australian_resident = cleaned_data.get('is_australian_resident')
        license_photo = cleaned_data.get('license_photo')
        international_license_photo = cleaned_data.get('international_license_photo')
        passport_photo = cleaned_data.get('passport_photo')
        license_number = cleaned_data.get('license_number')
        license_issuing_country = cleaned_data.get('license_issuing_country')
        passport_number = cleaned_data.get('passport_number')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')

        if is_australian_resident:
            if not license_photo:
                self.add_error('license_photo', "Australian residents must upload their domestic driver's license photo.")
            if not license_number:
                self.add_error('license_number', "Australian residents must provide their domestic license number.")
        else:
            if not international_license_photo:
                self.add_error('international_license_photo', "Foreign drivers must upload their International Driver's License photo.")
            if not passport_photo:
                self.add_error('passport_photo', "Foreign drivers must upload their passport photo.")
            if not license_issuing_country:
                self.add_error('license_issuing_country', "Foreign drivers must provide the issuing country of their International Driver's License.")
            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
        return cleaned_data