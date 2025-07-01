from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime

from users.models import User
from dashboard.models import HireSettings


class DriverProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='driver_profile',
        null=True, blank=True
    )

    phone_number = models.CharField(max_length=20, blank=False, null=False, help_text="Phone number of the driver.")
    address_line_1 = models.CharField(max_length=100, blank=False, null=False, help_text="Address line 1 of the driver.")
    address_line_2 = models.CharField(max_length=100, blank=True, null=True, help_text="Address line 2 of the driver.")
    city = models.CharField(max_length=50, blank=False, null=False, help_text="City of the driver.")
    state = models.CharField(max_length=50, blank=True, null=True, help_text="State of the driver.")
    post_code = models.CharField(max_length=20, blank=True, null=True, help_text="Postal code of the driver.")
    country = models.CharField(max_length=50, blank=False, null=False, help_text="Country of the driver.")

    name = models.CharField(max_length=100, blank=False, null=False, help_text="Full name of the driver.")
    email = models.EmailField(blank=False, null=False, help_text="Email address of the driver.")
    date_of_birth = models.DateField(blank=False, null=False, help_text="Date of birth of the driver.")

    is_australian_resident = models.BooleanField(
        default=False,
        help_text="Is the driver an Australian resident?"
    )

    license_number = models.CharField(max_length=50, blank=True, null=True, help_text="Driver's license number.")
    international_license_issuing_country = models.CharField(max_length=100, blank=True, null=True, help_text="Country that issued the International Driver's License.")
    license_expiry_date = models.DateField(null=True, blank=True, help_text="Expiry date of the license.")
    international_license_expiry_date = models.DateField(blank=True, null=True, help_text="Expiry date of the International Driver's License.")

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

    passport_number = models.CharField(max_length=50, blank=True, null=True, help_text="Passport number.")
    passport_expiry_date = models.DateField(blank=True, null=True, help_text="Passport expiry date.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return str(self.user)
        return self.name or self.email or self.phone_number or f"Anonymous Driver {self.pk}"

    def clean(self):
        super().clean()

        errors = {}
        today = timezone.now().date()
        if self.date_of_birth:
            try:
                settings = HireSettings.objects.first()
                if settings and settings.minimum_driver_age is not None:
                    age = today.year - self.date_of_birth.year -\
                          ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
                    if age < settings.minimum_driver_age:
                        errors['date_of_birth'] = f"Driver must be at least {settings.minimum_driver_age} years old."
            except HireSettings.DoesNotExist:
                pass
            except Exception as e:
                pass

        if self.is_australian_resident:
            if not self.license_photo:
                errors['license_photo'] = "Australian residents must upload their domestic driver's license photo."
            if not self.license_number:
                errors['license_number'] = "Australian residents must provide their domestic license number."
            if self.license_expiry_date and self.license_expiry_date < today:
                errors['license_expiry_date'] = "Australian domestic driver's license must not be expired."
            
        else:
            if not self.international_license_photo:
                errors[
                    'international_license_photo'] = "Foreign drivers must upload their International Driver's License photo."
            if not self.passport_photo:
                errors['passport_photo'] = "Foreign drivers must upload their passport photo."
            if not self.international_license_issuing_country:
                errors[
                    'international_license_issuing_country'] = "Foreign drivers must provide the issuing country of their International Driver's License."
            if not self.international_license_expiry_date:
                errors['international_license_expiry_date'] = "Foreign drivers must provide the expiry date of their International Driver's License."
            elif self.international_license_expiry_date and self.international_license_expiry_date < today:
                errors['international_license_expiry_date'] = "International Driver's License must not be expired."
            if not self.passport_number:
                errors['passport_number'] = "Foreign drivers must provide their passport number."
            if not self.passport_expiry_date:
                errors['passport_expiry_date'] = "Foreign drivers must provide their passport expiry date."
            elif self.passport_expiry_date and self.passport_expiry_date < today:
                errors['passport_expiry_date'] = "Passport must not be expired."
            
        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ['name', 'email']
        verbose_name = "Driver Profile"
        verbose_name_plural = "Driver Profiles"
