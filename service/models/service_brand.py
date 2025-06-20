from django.db import models

# Model for brands that can be worked on
class ServiceBrand(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Name of the service brand (e.g., 'Yamaha', 'Vespa').")
    image = models.ImageField(
        upload_to='brands/',
        null=True,
        blank=True,
        help_text="Optional image for this brand."
    )
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Service Brand"
        verbose_name_plural = "Service Brands"
        ordering = ['name']
