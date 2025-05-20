# hire/forms/step4_HasAccount_form.py
from django import forms
from ..models import DriverProfile
from django.core.exceptions import ValidationError

class Step4HasAccountForm(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ['phone', 'address', 'city', 'county', 'postcode', 'driving_license_number', 'passport_number']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'driverprofile'):
            try:
                driver_profile = user.driverprofile
                self.initial['phone'] = driver_profile.phone
                self.initial['address'] = driver_profile.address
                self.initial['city'] = driver_profile.city
                self.initial['county'] = driver_profile.county
                self.initial['postcode'] = driver_profile.postcode
                self.initial['driving_license_number'] = driver_profile.driving_license_number
                self.initial['passport_number'] = driver_profile.passport_number
            except DriverProfile.DoesNotExist:
                pass
        elif user:
            self.initial['phone'] = user.phone_number
            self.initial['address'] = user.address_line_1
            self.initial['city'] = user.city
            self.initial['county'] = user.state
            self.initial['postcode'] = user.post_code

    def clean(self):
        cleaned_data = super().clean()
        is_australian_resident = cleaned_data.get('is_australian_resident') # Assuming this is in the form (it's in the model)
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