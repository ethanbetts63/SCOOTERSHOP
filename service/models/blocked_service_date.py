from django.db import models
from django.core.exceptions import ValidationError


class BlockedServiceDate(models.Model):
    start_date = models.DateField(help_text="The start date of the blocked period.")
    end_date = models.DateField(
        help_text="The end date of the blocked period (inclusive)."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional description for the blocked period.",
    )

    def __str__(self):
        if self.start_date == self.end_date:
            return f"Blocked: {self.start_date.strftime('%Y-%m-%d')}"
        else:
            return f"Blocked: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot be before the start date."}
            )

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Blocked Service Date"
        verbose_name_plural = "Blocked Service Dates"
