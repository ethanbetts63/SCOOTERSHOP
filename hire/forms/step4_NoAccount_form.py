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
        self.temp_booking = kwargs.pop('temp_booking', None) # Store temp_booking for validation
        super().__init__(*args, **kwargs)

        # Conditionally set required status based on initial data or instance
        # This needs to be done carefully as 'is_australian_resident' might be a string from POST data
        # or a boolean from an instance.
        is_australian_resident_initial = self.initial.get('is_australian_resident')
        is_australian_resident_instance = self.instance.is_australian_resident if self.instance else None

        # Determine if the form is being initialized for an Australian resident
        # Prioritize POST data if available, otherwise use instance data
        if self.data and 'is_australian_resident' in self.data:
            is_australian_resident_value = (self.data['is_australian_resident'].lower() == 'true')
        elif is_australian_resident_initial is not None:
            is_australian_resident_value = (str(is_australian_resident_initial).lower() == 'true')
        elif is_australian_resident_instance is not None:
            is_australian_resident_value = is_australian_resident_instance
        else:
            is_australian_resident_value = True # Default to Australian if no info is provided

        if not is_australian_resident_value: # If not an Australian resident (i.e., foreign)
            self.fields['license_number'].required = False
            self.fields['license_expiry_date'].required = False
            self.fields['license_photo'].required = False # Also make license_photo not required for foreigners

            # Ensure international and passport fields are required for foreigners
            self.fields['international_license_photo'].required = True
            self.fields['international_license_issuing_country'].required = True
            self.fields['international_license_expiry_date'].required = True
            self.fields['passport_photo'].required = True
            self.fields['passport_number'].required = True
            self.fields['passport_expiry_date'].required = True
        else: # If an Australian resident
            self.fields['international_license_photo'].required = False
            self.fields['international_license_issuing_country'].required = False
            self.fields['international_license_expiry_date'].required = False
            self.fields['passport_photo'].required = False
            self.fields['passport_number'].required = False
            self.fields['passport_expiry_date'].required = False

            # Ensure Australian fields are required for Australians
            self.fields['license_number'].required = True
            self.fields['license_expiry_date'].required = True
            self.fields['license_photo'].required = True


    def clean(self):
        cleaned_data = super().clean()
        is_australian_resident = cleaned_data.get('is_australian_resident')
        license_photo = cleaned_data.get('license_photo')
        international_license_photo = cleaned_data.get('international_license_photo')
        international_license_issuing_country = cleaned_data.get('international_license_issuing_country')
        international_license_expiry_date = cleaned_data.get('international_license_expiry_date')
        passport_photo = cleaned_data.get('passport_photo')
        license_number = cleaned_data.get('license_number')
        license_expiry_date = cleaned_data.get('license_expiry_date')
        passport_number = cleaned_data.get('passport_number')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')

        # Get the return date from the temporary booking
        return_date = None
        if self.temp_booking and self.temp_booking.return_date:
            return_date = self.temp_booking.return_date

        # Convert 'True'/'False' strings from ChoiceField to actual booleans for clean method logic
        if isinstance(is_australian_resident, str):
            is_australian_resident = (is_australian_resident.lower() == 'true')

        if is_australian_resident:
            # These checks are now redundant if fields are set to required=True in __init__
            # but they provide custom error messages. Keep them for custom messages.
            if not license_photo:
                self.add_error('license_photo', "Australian residents must upload their domestic driver's license photo.")
            if not license_number:
                self.add_error('license_number', "Australian residents must provide their domestic license number.")
            if not license_expiry_date:
                self.add_error('license_expiry_date', "Australian residents must provide their domestic license expiry date.")
            elif return_date and license_expiry_date < return_date:
                self.add_error('license_expiry_date', "Your Australian Driver's License must not expire before the end of your booking.")
        else:  # Not an Australian Resident (Foreigner)
            # These checks are now redundant if fields are set to required=True in __init__
            # but they provide custom error messages. Keep them for custom messages.
            if not international_license_photo:
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
            
            if not passport_photo:
                self.add_error('passport_photo', "Foreign drivers must upload their passport photo.")
            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
            elif return_date and passport_expiry_date and passport_expiry_date < return_date:
                self.add_error('passport_expiry_date', "Your passport must not expire before the end of your booking.")
        return cleaned_data

