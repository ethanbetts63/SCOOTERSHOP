from django.db import models, transaction
from django.core.exceptions import ValidationError

class ServiceTerms(models.Model):
    content = models.TextField(
        default="Please enter the service terms content here."
    )
    version_number = models.PositiveIntegerField(
        unique=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Service Terms"
        verbose_name_plural = "Service Terms"
        ordering = ['-version_number']

    def __str__(self):
        status = 'Active' if self.is_active else 'Archived'
        return f"v{self.version_number} - Created: {self.created_at.strftime('%d %b %Y')} ({status})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.version_number:
            last_version = ServiceTerms.objects.all().order_by('version_number').last()
            self.version_number = (last_version.version_number + 1) if last_version else 1

        if self.is_active:
            with transaction.atomic():
                ServiceTerms.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)

    def clean(self):
        if not self.is_active and not ServiceTerms.objects.filter(is_active=True).exclude(pk=self.pk).exists():
             raise ValidationError("You cannot deactivate the only active Service Terms version. Please activate another version first.")
