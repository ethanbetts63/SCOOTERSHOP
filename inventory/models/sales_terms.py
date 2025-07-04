from django.db import models, transaction
from django.core.exceptions import ValidationError

class SalesTerms(models.Model):
    content = models.TextField(
        help_text="The full text of the terms and conditions for this version."
    )
    version_number = models.PositiveIntegerField(
        unique=True,
        blank=True,
        help_text="A unique version number for tracking. Automatically assigned on creation."
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Is this the currently active version to be shown to new customers?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time this version was created."
    )

    class Meta:
        verbose_name = "Terms and Conditions"
        verbose_name_plural = "Terms and Conditions"
        ordering = ['-version_number']

    def __str__(self):
        status = 'Active' if self.is_active else 'Archived'
        return f"v{self.version_number} - Created: {self.created_at.strftime('%d %b %Y')} ({status})"

    def save(self, *args, **kwargs):
        # Assign a version number if creating a new instance
        if not self.pk and not self.version_number:
            last_version = SalesTerms.objects.all().order_by('version_number').last()
            self.version_number = (last_version.version_number + 1) if last_version else 1

        # If the version being saved is marked as active...
        if self.is_active:
            # Use a transaction to ensure this operation is atomic and safe
            with transaction.atomic():
                # Find all OTHER versions that are currently active and set them to inactive.
                SalesTerms.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def clean(self):
        if not self.is_active and not SalesTerms.objects.filter(is_active=True).exclude(pk=self.pk).exists():
             raise ValidationError("You cannot deactivate the only active Terms and Conditions version. Please activate another version first.")

