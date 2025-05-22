from django.db import models

class BlockedHireDate(models.Model):
    """
    Model to store dates or date ranges when hire bookings are not available.
    """
    start_date = models.DateField(help_text="The start date of the blocked period.")
    end_date = models.DateField(help_text="The end date of the blocked period (inclusive).")
    description = models.CharField(max_length=255, blank=True, null=True, help_text="Optional description for the blocked period.")

    def __str__(self):
        # Ensure start_date and end_date are not None before formatting
        start_str = self.start_date.strftime('%Y-%m-%d') if self.start_date else 'N/A'
        end_str = self.end_date.strftime('%Y-%m-%d') if self.end_date else 'N/A'

        if self.start_date == self.end_date:
            return f"Blocked Hire: {start_str}"
        else:
            return f"Blocked Hire: {start_str} to {end_str}"

    class Meta:
        ordering = ['start_date']
        verbose_name = "Blocked Hire Date"
        verbose_name_plural = "Blocked Hire Dates"

