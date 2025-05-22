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
        # Pop the 'user' argument as it's not directly used by ModelForm's __init__
        # but might be used for custom logic if 'instance' is not provided.
        user = kwargs.pop('user', None)

        # Call the parent ModelForm's __init__ method first.
        # This will automatically populate the form fields if an 'instance' is provided
        # (which is now done in step4_HasAccount_view.py).
        super().__init__(*args, **kwargs)

        # The following block is now largely redundant if 'instance' is always passed
        # from the view. However, if the form might sometimes be initialized without
        # an instance (e.g., for a brand new user who doesn't have a DriverProfile yet),
        # this logic can provide initial data from the User model.
        # Given the current flow, where temp_booking.driver_profile is passed as instance,
        # this block might not be strictly necessary for pre-filling, but it doesn't hurt
        # if it's only setting initial values that would otherwise be empty.
        # The crucial part is that the 'instance' argument takes precedence for existing data.

        # If no instance was provided, or if you want to ensure basic user data
        # populates fields even if no DriverProfile exists yet for the user,
        # you can keep this part. However, if 'instance' is always expected,
        # this can be removed. For now, keeping it as a fallback for new profiles.
        if user and not self.instance.pk: # Only apply if no existing DriverProfile instance is loaded
            # Populate name and email from User model if available and not already set by instance
            if not self.initial.get('name') and user.first_name and user.last_name:
                self.initial['name'] = f"{user.first_name} {user.last_name}".strip()
            if not self.initial.get('email') and user.email:
                self.initial['email'] = user.email

            # Populate other fields from User model if they exist on the User model
            # and are not already set by an instance.
            # This handles cases where a user might have some address/phone info
            # on their User model but no DriverProfile yet.
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
        passport_number = cleaned_data.get('passport_number')
        passport_expiry_date = cleaned_data.get('passport_expiry_date')

        # Convert 'True'/'False' strings from ChoiceField to actual booleans
        if isinstance(is_australian_resident, str):
            is_australian_resident = (is_australian_resident.lower() == 'true')

        if is_australian_resident: # Now a boolean
            if not license_photo and not self.instance.license_photo: # Check if new photo uploaded or existing
                self.add_error('license_photo', "Australian residents must upload their domestic driver's license photo.")
            if not license_number:
                self.add_error('license_number', "Australian residents must provide their domestic license number.")
            # The DriverProfile model's clean method handles expiry dates and conditional fields,
            # so we can rely on that for more complex validation.
            # This form's clean method focuses on required file uploads based on residency.
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
            if not passport_number:
                self.add_error('passport_number', "Foreign drivers must provide their passport number.")
            if not passport_expiry_date:
                self.add_error('passport_expiry_date', "Foreign drivers must provide their passport expiry date.")
        return cleaned_data

