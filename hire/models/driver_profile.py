from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime

# Assuming your custom User model is in 'users.models'
from users.models import User
# Import HireSettings for age validation
from dashboard.models import HireSettings


class DriverProfile(models.Model):
    """
    Model to store information about a driver or renter.
    Can be linked to a registered User account or exist independently for anonymous bookings.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='driver_profile',
        null=True, blank=True
    )

    # --- Contact Information (From User model) ---
    # These fields are now explicitly required
    phone_number = models.CharField(max_length=20, blank=False, null=False, help_text="Phone number of the driver.")
    address_line_1 = models.CharField(max_length=100, blank=False, null=False, help_text="Address line 1 of the driver.")
    address_line_2 = models.CharField(max_length=100, blank=True, null=True, help_text="Address line 2 of the driver.")
    city = models.CharField(max_length=50, blank=False, null=False, help_text="City of the driver.")
    state = models.CharField(max_length=50, blank=True, null=True, help_text="State of the driver.")
    post_code = models.CharField(max_length=20, blank=True, null=True, help_text="Postal code of the driver.")
    country = models.CharField(max_length=50, blank=False, null=False, help_text="Country of the driver.")

    # --- Additional Contact and Identity Information ---
    # These fields are now explicitly required
    name = models.CharField(max_length=100, blank=False, null=False, help_text="Full name of the driver.")
    email = models.EmailField(blank=False, null=False, help_text="Email address of the driver.")
    date_of_birth = models.DateField(blank=False, null=False, help_text="Date of birth of the driver.")

    # --- Residency and Documentation ---
    is_australian_resident = models.BooleanField(
        default=False,
        help_text="Is the driver an Australian resident?"
    )

    # License details (Australian domestic for residents, International for foreigners)
    # license_expiry_date changed to null=True, blank=True
    license_number = models.CharField(max_length=50, blank=True, null=True, help_text="Driver's license number.")
    international_license_issuing_country = models.CharField(max_length=100, blank=True, null=True, help_text="Country that issued the International Driver's License.")
    license_expiry_date = models.DateField(null=True, blank=True, help_text="Expiry date of the license.") # Made nullable
    international_license_expiry_date = models.DateField(blank=True, null=True, help_text="Expiry date of the International Driver's License.")

    # Uploads (From User model)
    id_image = models.FileField(upload_to='user_ids/', blank=True, null=True, help_text="Image of the driver's ID.")
    international_id_image = models.FileField(upload_to='user_ids/international/', blank=True, null=True, help_text="Image of the driver's international ID.")
    license_photo = models.FileField(
        upload_to='driver_profiles/licenses/',
        blank=True, null=True, help_text="Upload of the driver's primary license (Australian domestic for residents)."
    )
    international_license_photo = models.FileField(
        upload_to='driver_profiles/international_licenses/',
        blank=True, null=True, help_text="Upload of the International Driver's License (required for foreigners)."
    )
    passport_photo = models.FileField(
        upload_to='driver_profiles/passports/',
        blank=True, null=True, help_text="Upload of the driver's passport (required for foreigners)."
    )

    # Passport details (required for Foreigners)
    passport_number = models.CharField(max_length=50, blank=True, null=True, help_text="Passport number.")
    passport_expiry_date = models.DateField(blank=True, null=True, help_text="Passport expiry date.")

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Methods ---
    def __str__(self):
        # Use user string or name/email for representation
        if self.user:
            return str(self.user)
        return self.name or self.email or self.phone_number or f"Anonymous Driver {self.pk}"

    def clean(self):
        """
        Custom validation for DriverProfile data.
        """
        super().clean()

        errors = {}  # Use an errors dictionary to collect all errors
        today = timezone.now().date()
        # --- Age Validation ---
        if self.date_of_birth:
            try:
                settings = HireSettings.objects.first()  # Get settings
                if settings and settings.minimum_driver_age is not None:
                    # Calculate age precisely
                    age = today.year - self.date_of_birth.year - \
                          ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
                    if age < settings.minimum_driver_age:
                        errors['date_of_birth'] = f"Driver must be at least {settings.minimum_driver_age} years old."
                        print(f"DEBUG: DriverProfile clean - Age validation error: {errors['date_of_birth']}")
            except HireSettings.DoesNotExist:
                print("DEBUG: DriverProfile clean - HireSettings not found for age validation.")
                pass
            except Exception as e:
                print(f"Error retrieving HireSettings for age validation: {e}")
                pass

        # --- Conditional Validation based on Residency ---
        if self.is_australian_resident:
            print("DEBUG: DriverProfile clean - Validating as Australian resident.")
            if not self.license_photo:
                errors['license_photo'] = "Australian residents must upload their domestic driver's license photo."
                print(f"DEBUG: DriverProfile clean - Error: {errors['license_photo']}")
            if not self.license_number:
                errors['license_number'] = "Australian residents must provide their domestic license number."
                print(f"DEBUG: DriverProfile clean - Error: {errors['license_number']}")
            # Only check expiry if license_expiry_date is provided (it's now nullable)
            if self.license_expiry_date and self.license_expiry_date < today:
                errors['license_expiry_date'] = "Australian domestic driver's license must not be expired."
                print(f"DEBUG: DriverProfile clean - Error: {errors['license_expiry_date']}")
            
            # Removed checks that disallowed international/passport fields for Australian residents
            # User wants to allow providing both sets of documents if they choose.

        else:  # Not an Australian Resident (Foreigner)
            print("DEBUG: DriverProfile clean - Validating as Foreign driver.")
            if not self.international_license_photo:
                errors[
                    'international_license_photo'] = "Foreign drivers must upload their International Driver's License photo."
                print(f"DEBUG: DriverProfile clean - Error: {errors['international_license_photo']}")
            if not self.passport_photo:
                errors['passport_photo'] = "Foreign drivers must upload their passport photo."
                print(f"DEBUG: DriverProfile clean - Error: {errors['passport_photo']}")
            if not self.international_license_issuing_country:
                errors[
                    'international_license_issuing_country'] = "Foreign drivers must provide the issuing country of their International Driver's License."
                print(f"DEBUG: DriverProfile clean - Error: {errors['international_license_issuing_country']}")
            if not self.international_license_expiry_date:
                errors['international_license_expiry_date'] = "Foreign drivers must provide the expiry date of their International Driver's License."
                print(f"DEBUG: DriverProfile clean - Error: {errors['international_license_expiry_date']}")
            elif self.international_license_expiry_date and self.international_license_expiry_date < today:
                errors['international_license_expiry_date'] = "International Driver's License must not be expired."
                print(f"DEBUG: DriverProfile clean - Error: {errors['international_license_expiry_date']}")
            if not self.passport_number:
                errors['passport_number'] = "Foreign drivers must provide their passport number."
                print(f"DEBUG: DriverProfile clean - Error: {errors['passport_number']}")
            if not self.passport_expiry_date:
                errors['passport_expiry_date'] = "Foreign drivers must provide their passport expiry date."
                print(f"DEBUG: DriverProfile clean - Error: {errors['passport_expiry_date']}")
            elif self.passport_expiry_date and self.passport_expiry_date < today:
                errors['passport_expiry_date'] = "Passport must not be expired."
                print(f"DEBUG: DriverProfile clean - Error: {errors['passport_expiry_date']}")
            
            # Removed check that disallowed Australian domestic license photo for foreign drivers.
            # User wants to allow providing both sets of documents if they choose.

        # --- Raise Errors ---
        if errors:
            print(f"DEBUG: DriverProfile clean - Raising ValidationError with errors: {errors}")
            raise ValidationError(errors)
        print("DEBUG: DriverProfile clean - No errors found in model clean.")

    class Meta:
        ordering = ['name', 'email']
        verbose_name = "Driver Profile"
        verbose_name_plural = "Driver Profiles"

