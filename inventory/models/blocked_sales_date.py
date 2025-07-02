from django.db import models
from django.core.exceptions import ValidationError


class BlockedSalesDate(models.Model):
    start_date = models.DateField(
        help_text="The start date of the blocked period for sales appointments."
    )
    end_date = models.DateField(
        help_text="The end date of the blocked period (inclusive) for sales appointments."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional description for the blocked period (e.g., 'Public Holiday', 'Staff Training').",
    )

    def __str__(self):
        if self.start_date == self.end_date:
            return f"Blocked Sales Date: {self.start_date.strftime('%Y-%m-%d')}"
        else:
            return (
                f"Blocked Sales Dates: {self.start_date.strftime('%Y-%m-%d')} "
                f"to {self.end_date.strftime('%Y-%m-%d')}"
            )

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot be before the start date."}
            )

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Blocked Sales Date"
        verbose_name_plural = "Blocked Sales Dates"
