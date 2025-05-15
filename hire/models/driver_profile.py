from django.db import models
# Assuming your custom User model is in 'users.models'
from users.models import User

# Model to store information about a driver or renter.
# This profile can be linked to a registered User account or exist independently for anonymous bookings.
class DriverProfile(models.Model):
    # Link to a registered User account (optional).
    # OneToOne ensures a User can only have one driver profile.
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE, # If the User is deleted, delete the profile.
        related_name='driver_profile',
        null=True, # Allow profiles that are not linked to a registered user (anonymous).
        blank=True
    )

    # --- Contact and Identity Information ---
    # Full name of the driver.
    name = models.CharField(max_length=100, help_text="Full name of the driver.")
    # Email address of the driver.
    email = models.EmailField(
        blank=True,
        null=True,
        # Consider if email should be unique=True here. If multiple anonymous profiles
        # could potentially use the same email over time, maybe not unique.
        # If you want to try and link future anonymous bookings by email, make it unique.
        # unique=True,
        help_text="Email address of the driver."
    )
    # Phone number of the driver.
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number of the driver.")
    # Physical address of the driver.
    address = models.TextField(blank=True, null=True, help_text="Physical address of the driver.")
    # Date of birth of the driver. Useful for age verification.
    date_of_birth = models.DateField(blank=True, null=True, help_text="Date of birth of the driver.")


    # --- Driver's License and Documentation ---
    # Driver's license number.
    license_number = models.CharField(max_length=50, blank=True, null=True, help_text="Driver's license number.")
    # Country that issued the driver's license.
    license_issuing_country = models.CharField(max_length=100, blank=True, null=True, help_text="Country that issued the license.")
    # Expiry date of the driver's license.
    license_expiry_date = models.DateField(blank=True, null=True, help_text="Expiry date of the license.")
    # Uploaded photo/scan of the primary driver's license.
    license_photo = models.FileField(
        upload_to='driver_profiles/licenses/',
        blank=True,
        null=True,
        help_text="Upload of the driver's primary license."
    )
    # Uploaded copy of the International Driver's License (if applicable).
    international_license_photo = models.FileField(
        upload_to='driver_profiles/international_licenses/',
        blank=True,
        null=True,
        help_text="Upload of the International Driver's License (if required)."
    )
    # Flag indicating if international license is required for this profile/driver.
    # This might be set based on the license_issuing_country and hire location.
    international_license_required = models.BooleanField(
        default=False,
        help_text="Is an International Driver's License required for this driver?"
    )


    # --- Timestamps ---
    # Timestamp when the profile was created.
    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when the profile was last updated.
    updated_at = models.DateTimeField(auto_now=True)

    # --- Methods ---
    # String representation of the driver profile.
    def __str__(self):
        # Show the user's email/username if linked, otherwise use name or email/phone from profile.
        if self.user:
            return str(self.user) # Or self.user.get_full_name() if available
        return self.name or self.email or self.phone or f"Anonymous Driver {self.pk}"

    # --- Meta Class ---
    class Meta:
        # Default ordering.
        ordering = ['name', 'email']
        # Verbose name for the model in the admin.
        verbose_name = "Driver Profile"
        verbose_name_plural = "Driver Profiles"

    # You might add a clean() method here to add validation,
    # e.g., ensuring name is present if user is null, or checking license expiry.
