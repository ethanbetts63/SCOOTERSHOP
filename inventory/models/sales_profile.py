from django.db import models


class SalesProfile(models.Model):

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="sales_profile",
        null=True,
        blank=True,
        help_text="Optional link to a registered user account.",
    )

    name = models.CharField(max_length=100, help_text="Full name of the customer.")
    email = models.EmailField(help_text="Email address of the customer.")
    phone_number = models.CharField(
        max_length=20, help_text="Phone number of the customer."
    )

    address_line_1 = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Address line 1 (e.g., street number and name).",
    )
    address_line_2 = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Address line 2 (e.g., apartment, suite, unit).",
    )
    city = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="City of the customer's address.",
    )
    state = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="State, province, or region of the customer's address.",
    )
    post_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Postal code or ZIP code of the customer's address.",
    )
    country = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Country of the customer's address.",
    )

    drivers_license_image = models.FileField(
        upload_to="drivers_licenses/",
        null=True,
        blank=True,
        help_text="Image of the customer's driver's license.",
    )
    drivers_license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Customer's driver's license number.",
    )
    drivers_license_expiry = models.DateField(
        null=True,
        blank=True,
        help_text="Expiration date of the customer's driver's license.",
    )

    date_of_birth = models.DateField(
        null=True, blank=True, help_text="Customer's date of birth."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time when this sales profile was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The date and time when this sales profile was last updated.",
    )

    class Meta:
        verbose_name = "Sales Profile"
        verbose_name_plural = "Sales Profiles"
        ordering = ["name"]

    def __str__(self):
        if self.user:
            return f"Sales Profile for {self.user.get_username()} ({self.name})"
        return f"Sales Profile for {self.name} ({self.email})"
