from django.db import models

# Model for brands that can be worked on
class ServiceBrand(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Name of the service brand (e.g., 'Yamaha', 'Vespa').")
    is_primary = models.BooleanField(default=False, help_text=f"Check if this is a primary brand to display prominently (limited to 5 total).")
    image = models.ImageField(
        upload_to='brands/',
        null=True,
        blank=True,
        help_text="Optional image for primary brands. Only used if 'Is Primary' is checked."
    )
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Only count other primary brands (exclude self if this is an update)
            query = ServiceBrand.objects.filter(is_primary=True)
            if self.pk:  # If updating an existing object
                query = query.exclude(pk=self.pk)

            if query.count() >= 5:
                raise ValueError(f"Cannot have more than 5 primary brands.")

        # Call the original save method
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Service Brand"
        verbose_name_plural = "Service Brands"
        ordering = ['name']
