from django.db import models

# Model defining types of service offered
class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    estimated_duration = models.DurationField(help_text="Estimated time to complete this service")
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True, help_text="Whether this service is currently offered")
    image = models.FileField(upload_to='service_types/', null=True, blank=True, help_text="Icon image for this service type")

    # String representation of the ServiceType instance
    def __str__(self):
        return self.name