from django.db import models


class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    estimated_duration_days = models.IntegerField(
        help_text="Estimated number of days to complete this service", null=True,
        blank=True
    )
    estimated_duration_hours = models.IntegerField(
        help_text="Estimated number of hours to complete this service", null=True,
        blank=True
    )
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_active = models.BooleanField(
        default=True, help_text="Whether this service is currently offered"
    )
    image = models.FileField(
        upload_to="service_types/",
        null=True,
        blank=True,
        help_text="Icon image for this service type",
    )
    slots_required = models.IntegerField(
        default=1,
        help_text="How many slots this service consumes."
    )

    class Meta:
        verbose_name = "Service Type"

        verbose_name_plural = "Service Types"

    def __str__(self):
        return self.name

    def clean(self):
        if self.estimated_duration_hours and not 1 <= self.estimated_duration_hours <= 23:
            raise ValidationError({'estimated_duration_hours': 'Ensure this value is between 1 and 23.'})
