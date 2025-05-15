from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone # Import timezone for date comparison
import datetime # Import datetime for age calculation

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
        null=True, blank=True # Allow anonymous profiles
    )

    # --- Contact and Identity Information ---
    name = models.CharField(max_length=100, help_text="Full name of the driver.")
    email = models.EmailField(blank=True, null=True, help_text="Email address of the driver.")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number of the driver.")
    address = models.TextField(blank=True, null=True, help_text="Physical address of the driver.")
    date_of_birth = models.DateField(blank=True, null=True, help_text="Date of birth of the driver.")

    # --- Residency and Documentation ---
    is_australian_resident = models.BooleanField(
        default=False,
        help_text="Is the driver an Australian resident?"
    )

    # License details (Australian domestic for residents, International for foreigners)
    # License number is only strictly required for Australian residents
    license_number = models.CharField(max_length=50, blank=True, null=True, help_text="Driver's license number.")
    license_issuing_country = models.CharField(max_length=100, blank=True, null=True, help_text="Country that issued the International Driver's License.")
    license_expiry_date = models.DateField(blank=True, null=True, help_text="Expiry date of the license.")

    # Uploads
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
        return self.name or self.email or self.phone or f"Anonymous Driver {self.pk}"

    def clean(self):
        """
        Custom validation for DriverProfile data.
        """
        super().clean()

        today = timezone.now().date()

        # --- Validation for Anonymous Profiles ---
        if not self.user:
            if not self.name:
                raise ValidationError("Name is required for anonymous profiles.")
            if not self.email and not self.phone:
                raise ValidationError("Either Email or Phone is required for anonymous profiles.")

        # --- Age Validation ---
        if self.date_of_birth:
            try:
                settings = HireSettings.objects.first() # Get settings
                if settings and settings.minimum_driver_age is not None:
                    # Calculate age precisely
                    age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
                    if age < settings.minimum_driver_age:
                        raise ValidationError(f"Driver must be at least {settings.minimum_driver_age} years old.")
            except HireSettings.DoesNotExist:
                 # Handle case where settings object doesn't exist (optional)
                 pass
            except Exception as e:
                 # Log or handle other potential errors getting settings
                 print(f"Error retrieving HireSettings for age validation: {e}")
                 pass # Allow saving if settings lookup fails unexpectedly


        # --- Conditional Validation based on Residency ---
        if self.is_australian_resident:
            # Requirements for Australian Residents
            if not self.license_photo:
                raise ValidationError("Australian residents must upload their domestic driver's license photo.")
            if not self.license_number:
                 raise ValidationError("Australian residents must provide their domestic license number.")
            if not self.license_expiry_date:
                raise ValidationError("Australian residents must provide their domestic license expiry date.")
            if self.license_expiry_date and self.license_expiry_date < today:
                raise ValidationError("Australian domestic driver's license must not be expired.")

            # Ensure foreigner fields are not used
            if self.international_license_photo:
                 raise ValidationError("International Driver's License photo should not be provided for Australian residents.")
            if self.passport_photo:
                 raise ValidationError("Passport photo should not be provided for Australian residents.")
            if self.passport_number:
                 raise ValidationError("Passport number should not be provided for Australian residents.")
            if self.passport_expiry_date:
                 raise ValidationError("Passport expiry date should not be provided for Australian residents.")
            # license_issuing_country is not required

        else: # Not an Australian Resident (Foreigner)
            # Requirements for Foreigners
            if not self.international_license_photo:
                raise ValidationError("Foreign drivers must upload their International Driver's License photo.")
            if not self.passport_photo:
                raise ValidationError("Foreign drivers must upload their passport photo.")
            if not self.license_issuing_country:
                 raise ValidationError("Foreign drivers must provide the issuing country of their International Driver's License.")
            if not self.license_expiry_date:
                # While license number is not required for international, expiry date is
                raise ValidationError("Foreign drivers must provide their International Driver's License expiry date.")
            if self.license_expiry_date and self.license_expiry_date < today:
                 raise ValidationError("International Driver's License must not be expired.")

            # Passport details required for foreigners
            if not self.passport_number:
                raise ValidationError("Foreign drivers must provide their passport number.")
            if not self.passport_expiry_date:
                raise ValidationError("Foreign drivers must provide their passport expiry date.")
            if self.passport_expiry_date and self.passport_expiry_date < today:
                raise ValidationError("Passport must not be expired.")

            # Ensure Australian resident license photo is not used
            if self.license_photo:
                raise ValidationError("Australian domestic driver's license photo should not be provided for foreign drivers.")
            # license_number is not required for foreigners and doesn't need explicit check here as it's blank=True, null=True


    class Meta:
        ordering = ['name', 'email']
        verbose_name = "Driver Profile"
        verbose_name_plural = "Driver Profiles"