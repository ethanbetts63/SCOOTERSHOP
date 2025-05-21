from django import forms
from ..models import DriverProfile
from django.core.exceptions import ValidationError


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
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'driverprofile'):
            try:
                driver_profile = user.driverprofile
                self.initial['name'] = driver_profile.name
                self.initial['email'] = driver_profile.email
                self.initial['phone_number'] = driver_profile.phone_number
                self.initial['address_line_1'] = driver_profile.address_line_1
                self.initial['address_line_2'] = driver_profile.address_line_2
                self.initial['city'] = driver_profile.city
                self.initial['state'] = driver_profile.state
                self.initial['post_code'] = driver_profile.post_code
                self.initial['country'] = driver_profile.country
                self.initial['date_of_birth'] = driver_profile.date_of_birth
                self.initial['is_australian_resident'] = driver_profile.is_australian_resident
                self.initial['license_number'] = driver_profile.license_number
                self.initial['license_expiry_date'] = driver_profile.license_expiry_date
                self.initial['international_license_photo'] = driver_profile.international_license_photo
                self.initial['international_license_issuing_country'] = driver_profile.international_license_issuing_country
                self.initial['international_license_expiry_date'] = driver_profile.international_license_expiry_date
                self.initial['passport_photo'] = driver_profile.passport_photo
                self.initial['passport_number'] = driver_profile.passport_number
                self.initial['passport_expiry_date'] = driver_profile.passport_expiry_date
                self.initial['id_image'] = driver_profile.id_image
                self.initial['international_id_image'] = driver_profile.international_id_image
                self.initial['license_photo'] = driver_profile.license_photo
            except DriverProfile.DoesNotExist:
                pass
        elif user:
            self.initial['phone_number'] = getattr(user, 'phone_number', None)
            self.initial['address_line_1'] = getattr(user, 'address_line_1', None)
            self.initial['address_line_2'] = getattr(user, 'address_line_2', None)
            self.initial['city'] = getattr(user, 'city', None)
            self.initial['state'] = getattr(user, 'state', None)
            self.initial['post_code'] = getattr(user, 'post_code', None)
            self.initial['country'] = getattr(user, 'country', None)

    def clean(self):
        cleaned_data = super().clean()
        is_australian_resident = cleaned_data.get('is_australian_resident')
        license_photo = cleaned_data.get('license_photo')
        international_license_photo = cleaned_data.get('international_license_photo')
        international_license_issuing_country = cleaned_data.get('international_license_issuing_country')
        international_license_expiry_date = cleaned_data.get('international_license_expiry_date')
        passport_photo = cleaned_data.get('passport_photo')
        license_number = cleaned_data.get('license_number')
        passport_number = cleaned_data.get('passport_number')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')

        if is_australian_resident == 'True':
            if not license_photo:
                self.add_error('license_photo', "Australian residents must upload their domestic driver's license photo.")
            if not license_number:
                self.add_error('license_number', "Australian residents must provide their domestic license number.")
        elif is_australian_resident == 'False':
            if not international_license_photo:
                self.add_error('international_license_photo',
                                "Foreign drivers must upload their International Driver's License photo.")
            if not international_license_issuing_country:
                self.add_error('international_license_issuing_country',
                                "Foreign drivers must provide the issuing country of their International Driver's License.")
            if not international_license_expiry_date:
                self.add_error('international_license_expiry_date',
                                "Foreign drivers must provide the expiry date of their International Driver's License.")
            if not passport_photo:
                self.add_error('passport_photo', "Foreign drivers must upload their passport photo.")
            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
        return cleaned_data