from django.db import models
from django.core.exceptions import ValidationError

class ServiceSettings(models.Model):
    """
    Dedicated settings for the service booking system.
    Typically, only one instance of this model should exist (singleton pattern often enforced at application level).
    """
    # General Booking Settings
    enable_service_booking = models.BooleanField(default=True, help_text="Globally enable or disable the service booking system.")
    booking_advance_notice = models.IntegerField(default=1, help_text="Minimum number of days notice required for a booking (e.g., 1 for next day).")
    max_visible_slots_per_day = models.IntegerField(default=6, help_text="Maximum number of booking slots to show per day in the calendar.")
    
    # User Types & Access
    allow_anonymous_bookings = models.BooleanField(default=True, help_text="Allow users to book without creating an account.")
    allow_account_bookings = models.BooleanField(default=True, help_text="Allow logged-in users to book.")

    # Operational Settings
    booking_open_days = models.CharField(
        max_length=255, default="Mon,Tue,Wed,Thu,Fri",
        help_text="Comma-separated list of days when bookings are open (e.g., Mon,Tue,Wed,Thu,Fri,Sat,Sun)."
    ) # Consider a more structured way if complex rules are needed (e.g., JSONField or separate model)
    
    enable_service_brands = models.BooleanField(default=True, help_text="Enable filtering or special handling by motorcycle brand.")
    other_brand_policy_text = models.TextField(
        blank=True,
        help_text="Policy text displayed to users when booking for an 'Other' brand motorcycle (e.g., regarding review, potential rejection, and refund policy)."
    )

    # Deposit Settings
    enable_deposit = models.BooleanField(default=False, help_text="Enable deposit requirement for bookings.")
    DEPOSIT_CALC_CHOICES = [
        ('FLAT_FEE', 'Flat Fee'),
        ('PERCENTAGE', 'Percentage of Booking Total'), # 'Booking Total' needs definition if services have variable prices
    ]
    deposit_calc_method = models.CharField(
        max_length=20, choices=DEPOSIT_CALC_CHOICES, default='FLAT_FEE',
        help_text="Method to calculate the deposit amount."
    )
    deposit_flat_fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Flat fee amount for deposit if 'Flat Fee' method is chosen."
    )
    deposit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, # e.g., 0.10 for 10%
        help_text="Percentage for deposit if 'Percentage' method is chosen (e.g., 0.1 for 10%)."
    )

    # Payment Options
    enable_online_full_payment = models.BooleanField(default=False, help_text="Allow customers to pay the full amount online.")
    enable_online_deposit = models.BooleanField(default=True, help_text="Allow customers to pay the deposit amount online (if deposits are enabled).")
    enable_instore_full_payment = models.BooleanField(default=True, help_text="Allow customers to opt for paying the full amount in-store.")
    
    # Currency
    currency_code = models.CharField(max_length=3, default='AUD', help_text="Currency code (e.g., AUD, USD).")
    currency_symbol = models.CharField(max_length=5, default='$', help_text="Currency symbol (e.g., $).")

    # Refund & Cancellation Policy (Full Payment)
    cancel_full_payment_max_refund_days = models.IntegerField(
        default=7, null=True, blank=True, help_text="Days before booking for maximum refund (e.g., 7 days for 100%)."
    )
    cancel_full_payment_max_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00, null=True, blank=True, help_text="Max refund percentage (e.g., 1.00 for 100%)."
    )
    cancel_full_payment_partial_refund_days = models.IntegerField(
        default=3, null=True, blank=True, help_text="Days before booking for partial refund (e.g., 3 days for 50%)."
    )
    cancel_full_payment_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.50, null=True, blank=True, help_text="Partial refund percentage (e.g., 0.50 for 50%)."
    )
    cancel_full_payment_min_refund_days = models.IntegerField(
        default=1, null=True, blank=True, help_text="Days before booking for minimum or no refund (e.g., 1 day for 0%)."
    )
    cancel_full_payment_min_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, null=True, blank=True, help_text="Min refund percentage (e.g., 0.00 for 0%)."
    )
    
    # Refund & Cancellation Policy (Deposit) - "Repeat cancellation variables for deposit"
    cancel_deposit_max_refund_days = models.IntegerField(
        default=7, null=True, blank=True, help_text="Days before booking for maximum deposit refund."
    )
    cancel_deposit_max_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00, null=True, blank=True, help_text="Max deposit refund percentage."
    )
    cancel_deposit_partial_refund_days = models.IntegerField(
        default=3, null=True, blank=True, help_text="Days before booking for partial deposit refund."
    )
    cancel_deposit_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.50, null=True, blank=True, help_text="Partial deposit refund percentage."
    )
    cancel_deposit_min_refund_days = models.IntegerField(
        default=1, null=True, blank=True, help_text="Days before booking for minimum or no deposit refund."
    )
    cancel_deposit_min_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, null=True, blank=True, help_text="Min deposit refund percentage."
    )
    
    # Stripe Fee consideration on refund (This is a policy point, actual handling is complex)
    refund_deducts_stripe_fee_policy = models.BooleanField(
        default=True, 
        help_text="Policy: If true, refunds (especially for admin declined 'Other' brand bookings) may have Stripe transaction fees deducted."
    )
    stripe_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.0290, null=True, blank=True, # e.g., 0.029 for 2.9%
        help_text="Stripe's percentage fee (e.g., 0.029 for 2.9%). For informational/calculation purposes."
    )
    stripe_fee_fixed = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.30, null=True, blank=True, # e.g., 0.30 for $0.30
        help_text="Stripe's fixed fee per transaction (e.g., 0.30 for $0.30). For informational/calculation purposes."
    )


    def __str__(self):
        return "Service Booking Settings"

    def clean(self):
        # Ensure percentages are within valid range (0.0 to 1.0)
        percentage_fields = [
            'deposit_percentage', 
            'cancel_full_payment_max_refund_percentage', 'cancel_full_payment_partial_refund_percentage', 'cancel_full_payment_min_refund_percentage',
            'cancel_deposit_max_refund_percentage', 'cancel_deposit_partial_refund_percentage', 'cancel_deposit_min_refund_percentage',
            'stripe_fee_percentage'
        ]
        for field_name in percentage_fields:
            value = getattr(self, field_name)
            if value is not None and not (0 <= value <= 1):
                if field_name == 'stripe_fee_percentage' and not (0 <= value <= 0.1): # Stripe fees are usually small percentages
                     raise ValidationError({field_name: f"Ensure {field_name.replace('_', ' ')} is a sensible rate (e.g., 0.01 to 0.1 for 1-10%)."})
                elif field_name != 'stripe_fee_percentage':
                     raise ValidationError({field_name: f"Ensure {field_name.replace('_', ' ')} is between 0.00 (0%) and 1.00 (100%)."})


    def save(self, *args, **kwargs):
        # Enforce singleton: only one instance of ServiceSettings.
        # This is a common way to handle it, but can be done via admin restrictions too.
        if not self.pk and ServiceSettings.objects.exists():
            raise ValidationError("Only one instance of ServiceSettings can be created. Please edit the existing one.")
        self.full_clean() # Call clean method before saving
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Service Settings"
        verbose_name_plural = "Service Settings"