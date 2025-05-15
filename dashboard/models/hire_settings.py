from django.db import models

DEPOSIT_CALC_CHOICES = [
    ('percentage', 'Percentage of Total'),
    ('fixed', 'Fixed Amount')
]

class HireSettings(models.Model):
    # --- Rate Defaults ---
    # Default daily rate for bikes.
    default_hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True, 
        help_text="Default hourly rate for bikes if no custom rate is set (optional)."
    )

    default_daily_rate = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Default daily rate for bikes if no custom rate is set."
    )
    
    # Default weekly rate for bikes.
    default_weekly_rate = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Default weekly rate for bikes."
    )
    
    # Default monthly rate for bikes.
    default_monthly_rate = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Default monthly rate for bikes."
    )

    # --- Deposit Defaults ---
    # Enable deposit option.
    deposit_enabled = models.BooleanField(
        default=False,
        help_text="If enabled, customers can book by paying a deposit instead of the full amount upfront."
    )
    
    # Method for default deposit calculation.
    default_deposit_calculation_method = models.CharField(
        max_length=10,
        choices=DEPOSIT_CALC_CHOICES,
        default='percentage',
        help_text="How the default deposit is calculated when enabled."
    )
    
    # Default percentage for deposit.
    deposit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=10.00,
        help_text="Default percentage for deposit calculation."
    )
    
    # Default fixed amount for deposit.
    deposit_amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=50.00,
        help_text="Default fixed amount for deposit calculation."
    )

    # --- Feature Toggles ---
    # Enable individual add-ons.
    add_ons_enabled = models.BooleanField(
        default=True,
        help_text="Enable the option for customers to add individual add-ons."
    )
    
    # Enable add-on packages.
    packages_enabled = models.BooleanField(
        default=True,
        help_text="Enable the option for customers to select add-on packages."
    )

    # --- Hire Duration and Timing Rules ---
    # Minimum hire duration in days.
    minimum_hire_duration_days = models.PositiveIntegerField(
        default=1,
        help_text="Minimum duration for a hire booking in days."
    )
    
    # Minimum hours required before pickup.
    booking_lead_time_hours = models.PositiveIntegerField(
        default=2,
        help_text="Minimum hours required between booking time and pickup time."
    )
    
    # Grace period for late returns.
    grace_period_minutes = models.PositiveIntegerField(default=0, help_text="Grace period after return time before late fees apply.")

    # --- Additional Hire Settings from SiteSettings ---
    maximum_hire_duration_days = models.IntegerField(default=30, help_text="Maximum number of days for a hire booking")
    hire_confirmation_email_subject = models.CharField(max_length=200, default="Your motorcycle hire booking has been confirmed", help_text="Subject line for hire booking confirmation emails")
    admin_hire_notification_email = models.EmailField(blank=True, null=True, help_text="Email address for hire booking notifications")

    # --- Late Fees and Charges ---
    # Fee charged per hour for late returns.
    late_fee_per_hour = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True, blank=True,
        help_text="Fee charged per hour for late returns (if applicable).")
    
    # Fee charged per day for late returns.
    late_fee_per_day = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True, blank=True,
        help_text="Fee charged per full day for late returns (if applicable).")
    
    # Enable cleaning fee option.
    enable_cleaning_fee = models.BooleanField(
        default=False,
        help_text="Enable the option to charge a cleaning fee.")
    
    # Default cleaning fee amount.
    default_cleaning_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True, blank=True,
        help_text="Default amount for a cleaning fee.")

    # --- Driver Requirements ---
    # Minimum driver age required.
    minimum_driver_age = models.PositiveIntegerField(
        default=18, help_text="Minimum age required to be a driver.")
    
    # Age limit for young driver surcharge.
    young_driver_surcharge_age_limit = models.PositiveIntegerField(
        default=25,
        help_text="Age limit below which a young driver surcharge might apply.")
    
    # Require driver license upload.
    require_driver_license_upload = models.BooleanField(default=False, help_text="Require customers to upload driver license copies during booking.")

    # --- Currency Settings ---
    # Primary currency code.
    currency_code = models.CharField(max_length=3, default='DKK', help_text="The primary currency code (ISO 4217) for all prices and calculations.")
    
    # Currency symbol.
    currency_symbol = models.CharField(max_length=5, default='kr.', help_text="Symbol for the currency.")


    # --- Cancellation Policy ---
    # Full refund threshold in days.
    cancellation_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund if cancelled this many *full days* or more before pickup time."
    )
    # Partial refund threshold in days.
    cancellation_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund if cancelled this many *full days* or more (but less than full refund threshold) before pickup time."
    )
    # Percentage for partial refund.
    cancellation_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=50.00,
        help_text="Percentage of total hire price to refund for partial cancellations."
    )
    # Minimal refund threshold in days.
    cancellation_minimal_refund_days = models.PositiveIntegerField(
         default=1,
         help_text="Minimal refund percentage applies if cancelled this many *full days* or more (but less than partial refund threshold) before pickup time."
    )
    # Percentage for minimal refund.
    cancellation_minimal_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00,
        help_text="Percentage of total hire price to refund for late cancellations."
    )

    # Ensures only one instance exists.
    def save(self, *args, **kwargs):
        if not self.pk and HireSettings.objects.exists():
            existing = HireSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    # String representation of settings.
    def __str__(self):
        return "Hire Settings"

    class Meta:
        verbose_name = "Hire Settings"
        verbose_name_plural = "Hire Settings"