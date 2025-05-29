# dashboard/forms/driver_profile_form.py

from django import forms
from hire.models.driver_profile import DriverProfile
from users.models import User # Import the User model

class DriverProfileForm(forms.ModelForm):
    """
    Form for creating and updating DriverProfile instances.
    """
    # Custom field for 'user' to display full name and phone number
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('first_name', 'last_name'), # Order for consistent display
        required=False, # User link is optional as per model
        empty_label="-- Select an existing user (optional) --",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Link this driver profile to an existing user account."
    )

    class Meta:
        model = DriverProfile
        # Include all fields from the DriverProfile model, including 'user'
        fields = '__all__'
        # Exclude 'created_at', 'updated_at' as they are managed automatically
        exclude = ['created_at', 'updated_at']

        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'license_expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'international_license_expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'passport_expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'post_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_australian_resident': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'international_license_issuing_country': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control'}),
            # File fields don't need 'class': 'form-control' directly, but can be styled via CSS
            'id_image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'international_id_image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'license_photo': forms.FileInput(attrs={'class': 'form-control-file'}),
            'international_license_photo': forms.FileInput(attrs={'class': 'form-control-file'}),
            'passport_photo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            'user': "Link to Existing User", # Custom label for the user field
            'phone_number': "Phone Number",
            'address_line_1': "Address Line 1",
            'address_line_2': "Address Line 2",
            'city': "City",
            'state': "State/Province",
            'post_code': "Postal Code",
            'country': "Country",
            'name': "Full Name",
            'email': "Email Address",
            'date_of_birth': "Date of Birth",
            'is_australian_resident': "Australian Resident?",
            'license_number': "Primary License Number",
            'license_expiry_date': "Primary License Expiry Date",
            'international_license_issuing_country': "International License Issuing Country",
            'international_license_expiry_date': "International License Expiry Date",
            'passport_number': "Passport Number",
            'passport_expiry_date': "Passport Expiry Date",
            'id_image': "ID Image (e.g., Driver's License Front/Back, Passport Photo Page)",
            'international_id_image': "International ID Image (if applicable)",
            'license_photo': "Primary License Photo (Australian Domestic for residents)",
            'international_license_photo': "International Driver's License Photo (for foreign drivers)",
            'passport_photo': "Passport Photo (for foreign drivers)",
        }
        help_texts = {
            'is_australian_resident': "Check if the driver is an Australian resident. This affects required documentation.",
            'license_number': "Your primary driver's license number (e.g., Australian domestic license).",
            'license_expiry_date': "The expiry date of your primary driver's license.",
            'international_license_issuing_country': "The country that issued your International Driver's License.",
            'international_license_expiry_date': "The expiry date of your International Driver's License.",
            'passport_number': "Your passport number (required for foreign drivers).",
            'passport_expiry_date': "The expiry date of your passport (required for foreign drivers).",
            'id_image': "Upload a clear image of your primary identification (e.g., front/back of driver's license, or passport photo page).",
            'international_id_image': "If you have an international ID, upload an image of it here.",
            'license_photo': "Upload a clear photo of your Australian domestic driver's license (front and back if applicable).",
            'international_license_photo': "Upload a clear photo of your International Driver's License.",
            'passport_photo': "Upload a clear photo of your passport's main page.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap form-control class to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.DateInput, forms.Textarea, forms.Select)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control-file'})

        # Set custom choices for the 'user' field
        # This is done here to ensure it uses the custom label_from_instance
        self.fields['user'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.phone_number or 'N/A'})"


        # Initial state for conditional fields based on is_australian_resident
        # These fields are initially hidden/disabled and will be controlled by JS
        # The 'required' attribute is handled by the clean method in the model
        if 'is_australian_resident' in self.initial and not self.initial['is_australian_resident']:
            # If not Australian resident, make Australian-specific fields not required in form (model clean handles actual validation)
            self.fields['license_number'].required = False
            self.fields['license_photo'].required = False
            self.fields['license_expiry_date'].required = False # This field is always required by model, but we can set to False in form for conditional display
        elif 'is_australian_resident' in self.initial and self.initial['is_australian_resident']:
            # If Australian resident, make international/passport fields not required in form
            self.fields['international_license_issuing_country'].required = False
            self.fields['international_license_expiry_date'].required = False
            self.fields['international_license_photo'].required = False
            self.fields['passport_number'].required = False
            self.fields['passport_expiry_date'].required = False
            self.fields['passport_photo'].required = False
        else: # For new forms (no initial data)
            # By default, assume Australian resident for initial display, or handle with JS
            # For simplicity, we'll let JS manage initial visibility based on checkbox state
            pass

