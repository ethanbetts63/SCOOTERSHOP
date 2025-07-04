from django.db import models


class ServiceBrand(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the service brand (e.g., 'Yamaha', 'Vespa').",
    )
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Service Brand"
        verbose_name_plural = "Service Brands"
        ordering = ["name"]
