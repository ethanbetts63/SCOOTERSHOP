from django.db import models

# New model for blocked dates
class BlockedServiceDate(models.Model):
    """
    Model to store dates or date ranges when service bookings are not available.
    """
    start_date = models.DateField(help_text="The start date of the blocked period.")
    end_date = models.DateField(help_text="The end date of the blocked period (inclusive).")
    description = models.CharField(max_length=255, blank=True, null=True, help_text="Optional description for the blocked period.")

    def __str__(self):
        if self.start_date == self.end_date:
            return f"Blocked: {self.start_date.strftime('%Y-%m-%d')}"
        else:
            return f"Blocked: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['start_date']
        verbose_name = "Blocked Service Date"
        verbose_name_plural = "Blocked Service Dates"
