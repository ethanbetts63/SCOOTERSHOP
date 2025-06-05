from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import time

class ServiceSettings(models.Model):
    """
    Dedicated settings for the service booking system.
    Typically, only one instance of this model should exist (singleton pattern often enforced at application level).
    """
    # General Booking Settings
    enable_service_booking = models.BooleanField(default=True, help_text="Globally enable or disable the service booking system.")
    booking_advance_notice = models.IntegerField(default=1, help_text="Minimum number of days notice required for a booking (e.g., 1 for next day).")
    max_visible_slots_per_day = models.IntegerField(default=2, help_text="Maximum number of booking slots to show per day in the calendar.")
    
    # User Types & Access
    allow_anonymous_bookings = models.BooleanField(default=True, help_text="Allow users to book without creating an account.")
    allow_account_bookings = models.BooleanField(default=True, help_text="Allow logged-in users to book.")

    # Operational Settings
    booking_open_days = models.CharField(
        max_length=255, default="Mon,Tue,Wed,Thu,Fri",
        help_text="Comma-separated list of days when bookings are open (e.g., Mon,Tue,Wed,Thu,Fri,Sat,Sun)."
    )
    
    drop_off_start_time = models.TimeField(default=time(9, 0), help_text="The earliest time customers can drop off their motorcycle.")
    drop_off_end_time = models.TimeField(default=time(17, 0), help_text="The latest time customers can drop off their motorcycle.")
    
    # New field: Minimum interval in minutes between two booking drop offs on the same day.
    drop_off_spacing_mins = models.IntegerField(default=30, help_text="The minimum interval in minutes between two booking drop offs on the same day.")

    # New field: Maximum days in advance a customer can drop off their bike before the service date.
    max_advance_dropoff_days = models.IntegerField(
        default=0, # Default to 0, meaning drop-off must be on the service date or later (before service)
        help_text="Maximum number of days in advance a customer can drop off their motorcycle before the service date."
    )

    # New field: Latest time a customer can drop off their bike on the same day as the service.
    latest_same_day_dropoff_time = models.TimeField(
        default=time(12, 0), # Default to 12:00 PM (noon)
        help_text="The latest time a customer can drop off their motorcycle if the drop-off date is the same as the service date."
    )

    enable_service_brands = models.BooleanField(default=True, help_text="Enable filtering or special handling by motorcycle brand.")
    other_brand_policy_text = models.TextField(
        blank=True,
        help_text="Policy text displayed to users when booking for an 'Other' brand motorcycle (e.g., regarding review, potential rejection, and refund policy)."
    )

    # Deposit Settings
    enable_deposit = models.BooleanField(default=False, help_text="Enable deposit requirement for bookings.")
    DEPOSIT_CALC_CHOICES = [
        ('FLAT_FEE', 'Flat Fee'),
        ('PERCENTAGE', 'Percentage of Booking Total'),
    ]
    deposit_calc_method = models.CharField(
        max_length=20, choices=DEPOSIT_CALC_CHOICES, default='FLAT_FEE',
        help_text="Method to calculate the deposit amount."
    )
    deposit_flat_fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Flat fee amount for deposit if 'Flat Fee' method is chosen."
    )
    deposit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
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
        max_digits=5, decimal_places=2, default=Decimal('1.00'), null=True, blank=True, help_text="Max refund percentage (e.g., 1.00 for 100%)."
    )
    cancel_full_payment_partial_refund_days = models.IntegerField(
        default=3, null=True, blank=True, help_text="Days before booking for partial refund (e.g., 3 days for 50%)."
    )
    cancel_full_payment_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.50'), null=True, blank=True, help_text="Partial refund percentage (e.g., 0.50 for 50%)."
    )
    cancel_full_payment_min_refund_days = models.IntegerField(
        default=1, null=True, blank=True, help_text="Days before booking for minimum or no refund (e.g., 1 day for 0%)."
    )
    cancel_full_payment_min_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'), null=True, blank=True, help_text="Min refund percentage (e.g., 0.00 for 0%)."
    )
    
    # Refund & Cancellation Policy (Deposit)
    cancel_deposit_max_refund_days = models.IntegerField(
        default=7, null=True, blank=True, help_text="Days before booking for maximum deposit refund."
    )
    cancel_deposit_max_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('1.00'), null=True, blank=True, help_text="Max deposit refund percentage."
    )
    cancel_deposit_partial_refund_days = models.IntegerField(
        default=3, null=True, blank=True, help_text="Days before booking for partial deposit refund."
    )
    cancel_deposit_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.50'), null=True, blank=True, help_text="Partial deposit refund percentage."
    )
    cancel_deposit_min_refund_days = models.IntegerField(
        default=1, null=True, blank=True, help_text="Days before booking for minimum or no deposit refund."
    )
    cancel_deposit_min_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'), null=True, blank=True, help_text="Min deposit refund percentage."
    )
    
    # Stripe Fee consideration on refund
    refund_deducts_stripe_fee_policy = models.BooleanField(
        default=True, 
        help_text="Policy: If true, refunds (especially for admin declined 'Other' brand bookings) may have Stripe transaction fees deducted."
    )

    # New fields for domestic and international Stripe fees
    stripe_fee_percentage_domestic = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal('0.0170'),
        help_text="Stripe's percentage fee for domestic cards (e.g., 0.0170 for 1.70%)."
    )
    stripe_fee_fixed_domestic = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.30'),
        help_text="Stripe's fixed fee per transaction for domestic cards (e.g., 0.30 for A$0.30)."
    )
    stripe_fee_percentage_international = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal('0.0350'),
        help_text="Stripe's percentage fee for international cards (e.g., 0.0350 for 3.5%)."
    )
    stripe_fee_fixed_international = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.30'),
        help_text="Stripe's fixed fee per transaction for international cards (e.30 for A$0.30)."
    )


    def __str__(self):
        return "Service Settings"

    def clean(self):
        errors = {}

        start_time = self.drop_off_start_time
        end_time = self.drop_off_end_time
        latest_same_day_dropoff = self.latest_same_day_dropoff_time

        if start_time and end_time and start_time >= end_time:
            errors['drop_off_start_time'] = ["Booking start time must be earlier than end time."]
            errors['drop_off_end_time'] = ["Booking end time must be earlier than start time."]

        # Validate drop_off_spacing_mins
        if self.drop_off_spacing_mins is not None and (self.drop_off_spacing_mins <= 0 or self.drop_off_spacing_mins > 60):
            errors['drop_off_spacing_mins'] = ["Drop-off spacing must be a positive integer, typically between 1 and 60 minutes."]

        # Validate max_advance_dropoff_days
        if self.max_advance_dropoff_days is not None and self.max_advance_dropoff_days < 0:
            errors['max_advance_dropoff_days'] = ["Maximum advance drop-off days cannot be negative."]
        
        # Validate latest_same_day_dropoff_time is within drop_off_start_time and drop_off_end_time
        if latest_same_day_dropoff and (latest_same_day_dropoff < start_time or latest_same_day_dropoff > end_time):
            errors['latest_same_day_dropoff_time'] = [f"Latest same-day drop-off time must be between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}, inclusive."]


        general_percentage_fields = [
            'deposit_percentage',
            'cancel_full_payment_max_refund_percentage', 'cancel_full_payment_partial_refund_percentage', 'cancel_full_payment_min_refund_percentage',
            'cancel_deposit_max_refund_percentage', 'cancel_deposit_partial_refund_percentage', 'cancel_deposit_min_refund_percentage',
        ]
        for field_name in general_percentage_fields:
            value = getattr(self, field_name)
            if value is not None and not (Decimal('0.00') <= value <= Decimal('1.00')):
                errors[field_name] = [f"Ensure {field_name.replace('_', ' ')} is between 0.00 (0%) and 1.00 (100%)."]

        if self.stripe_fee_percentage_domestic is not None and not (Decimal('0.00') <= self.stripe_fee_percentage_domestic <= Decimal('0.10')):
            errors['stripe_fee_percentage_domestic'] = ["Ensure domestic stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."]
        
        if self.stripe_fee_percentage_international is not None and not (Decimal('0.00') <= self.stripe_fee_percentage_international <= Decimal('0.10')):
            errors['stripe_fee_percentage_international'] = ["Ensure international stripe fee percentage is a sensible rate (e.00 to 0.10 for 0-10%)."]

        max_full_days = self.cancel_full_payment_max_refund_days
        partial_full_days = self.cancel_full_payment_partial_refund_days
        min_full_days = self.cancel_full_payment_min_refund_days

        if max_full_days is not None and partial_full_days is not None and max_full_days < partial_full_days:
            errors['cancel_full_payment_max_refund_days'] = ["Max refund days must be greater than or equal to partial refund days."]
        if partial_full_days is not None and min_full_days is not None and partial_full_days < min_full_days:
            errors['cancel_full_payment_partial_refund_days'] = ["Partial refund days must be greater than or equal to min refund days."]

        max_deposit_days = self.cancel_deposit_max_refund_days
        partial_deposit_days = self.cancel_deposit_partial_refund_days
        min_deposit_days = self.cancel_deposit_min_refund_days

        if max_deposit_days is not None and partial_deposit_days is not None and max_deposit_days < partial_deposit_days:
            errors['cancel_deposit_max_refund_days'] = ["Max deposit refund days must be greater than or equal to partial deposit refund days."]
        if partial_deposit_days is not None and min_deposit_days is not None and partial_deposit_days < min_deposit_days:
            errors['cancel_deposit_partial_refund_days'] = ["Partial deposit refund days must be greater than or equal to min deposit refund days."]


        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):
        if not self.pk and ServiceSettings.objects.exists():
            raise ValidationError("Only one instance of ServiceSettings can be created. Please edit the existing one.")
        
        self.full_clean()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Service Settings"
        verbose_name_plural = "Service Settings"
