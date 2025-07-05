from django.db import models, transaction
from django.core.exceptions import ValidationError

class ServiceTerms(models.Model):
    """
    Represents a specific version of the Service Terms and Conditions.
    """
    content = models.TextField(
        help_text="The full text of the service terms for this version."
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
        verbose_name = "Service Terms"
        verbose_name_plural = "Service Terms"
        ordering = ['-version_number']

    def __str__(self):
        """
        String representation of the ServiceTerms object.
        """
        status = 'Active' if self.is_active else 'Archived'
        return f"v{self.version_number} - Created: {self.created_at.strftime('%d %b %Y')} ({status})"

    def save(self, *args, **kwargs):
        """
        Overrides the save method to handle versioning and activation.
        - Assigns an incremental version number to new instances.
        - Ensures only one version is active at a time.
        """
        # Assign a version number if creating a new instance
        if not self.pk and not self.version_number:
            last_version = ServiceTerms.objects.all().order_by('version_number').last()
            self.version_number = (last_version.version_number + 1) if last_version else 1

        # If the version being saved is marked as active, deactivate all others.
        if self.is_active:
            with transaction.atomic():
                ServiceTerms.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)

    def clean(self):
        """
        Custom validation to prevent deactivating the only active version.
        """
        if not self.is_active and not ServiceTerms.objects.filter(is_active=True).exclude(pk=self.pk).exists():
             raise ValidationError("You cannot deactivate the only active Service Terms version. Please activate another version first.")
