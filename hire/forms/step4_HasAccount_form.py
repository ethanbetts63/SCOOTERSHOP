# hire/forms/step4_HasAccount_form.py
from django import forms
from ..models import DriverProfile
from django.core.exceptions import ValidationError


class Step4HasAccountForm(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = [
            'phone_number',  # Updated field name
            'address_line_1',  # Updated field name
            'address_line_2',  # Added field
            'city',
            'state',  # Updated field name
            'post_code',  # Updated field name
            'country',  # Added field
            'license_number',  # Updated field name
            'passport_number',
            'id_image',  # Added field
            'international_id_image',  # Added field
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'driverprofile'):
            try:
                driver_profile = user.driverprofile
                self.initial['phone_number'] = driver_profile.phone_number  # Updated field name
                self.initial['address_line_1'] = driver_profile.address_line_1  # Updated field name
                self.initial['address_line_2'] = driver_profile.address_line_2  # Added field
                self.initial['city'] = driver_profile.city
                self.initial['state'] = driver_profile.state  # Updated field name
                self.initial['post_code'] = driver_profile.post_code  # Updated field name
                self.initial['country'] = driver_profile.country  # Added field
                self.initial['license_number'] = driver_profile.license_number  # Updated field name
                self.initial['passport_number'] = driver_profile.passport_number
                self.initial['id_image'] = driver_profile.id_image  # Added field
                self.initial['international_id_image'] = driver_profile.international_id_image  # Added field
            except DriverProfile.DoesNotExist:
                pass
        elif user:
            self.initial['phone_number'] = user.phone_number  # Updated field name
            self.initial['address_line_1'] = user.address_line_1  # Updated field name
            self.initial['address_line_2'] = user.address_line_2  # Added field
            self.initial['city'] = user.city
            self.initial['state'] = user.state  # Updated field name
            self.initial['post_code'] = user.post_code  # Updated field name
            self.initial['country'] = user.country  # Added field

    def clean(self):
        cleaned_data = super().clean()
        is_australian_resident = cleaned_data.get('is_australian_resident')  # Assuming this is in the form (it's in the model)
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
                self.add_error('international_license_photo',
                               "Foreign drivers must upload their International Driver's License photo.")
            if not passport_photo:
                self.add_error('passport_photo', "Foreign drivers must upload their passport photo.")
            if not license_issuing_country:
                self.add_error('license_issuing_country',
                               "Foreign drivers must provide the issuing country of their International Driver's License.")
            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
        return cleaned_data