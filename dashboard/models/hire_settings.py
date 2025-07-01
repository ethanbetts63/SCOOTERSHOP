                              

from django.db import models
from datetime import time

DEPOSIT_CALC_CHOICES = [
    ('percentage', 'Percentage of Total'),
    ('fixed', 'Fixed Amount')
]

                                                  
HIRE_PRICING_STRATEGY_CHOICES = [
    ('flat_24_hour', 'Flat 24-Hour Billing (Any excess rounds to full day)'),
    ('24_hour_plus_margin', '24-Hour Billing with Margin (Excess hours within margin are free, then full day)'),
    ('24_hour_customer_friendly', '24-Hour Billing Friendly (Excess hours are billed at hourly rate or day rate, whichever is lower)'),
    ('daily_plus_excess_hourly', 'Daily Rate + Excess Hourly (Every additional hour charged hourly)'),
    ('daily_plus_proportional_excess', 'Daily Rate + Proportional Excess (Excess hours billed as percentage of daily rate)'),
    ('24_hour_plus_margin_proportional', '24-Hour Billing with Margin + Proportional (Excess hours beyond margin are proportional)'),
]


class HireSettings(models.Model):
                           
                                    
    default_hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Default hourly rate for bikes if no custom rate is set (optional)."
    )

    default_daily_rate = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=0.00,
        help_text="Default daily rate for bikes if no custom rate is set."
    )

                         
    weekly_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00,
        help_text="Discount percentage for hires of 7 days or more."
    )

    monthly_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00,
        help_text="Discount percentage for hires of 30 days or more."
    )

                             
    enable_online_full_payment = models.BooleanField(
        default=False,
        help_text="Allow customers to pay the full amount online."
    )
    enable_online_deposit_payment = models.BooleanField(
        default=False,
        help_text="Allow customers to pay a deposit online."
    )
    enable_in_store_full_payment = models.BooleanField(
        default=False,
        help_text="Allow customers to pay the full amount in store."
    )

                              
                            
    deposit_enabled = models.BooleanField(
        default=False,
        help_text="If enabled, customers can book by paying a deposit instead of the full amount upfront."
    )

                                             
    default_deposit_calculation_method = models.CharField(
        max_length=10,
        choices=DEPOSIT_CALC_CHOICES,
        default='percentage',
        help_text="How the default deposit is calculated when enabled."
    )

                                     
    deposit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=10.00,
        help_text="Default percentage for deposit calculation."
    )

                                       
    deposit_amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=50.00,
        help_text="Default fixed amount for deposit calculation."
    )

                             
                                
    add_ons_enabled = models.BooleanField(
        default=True,
        help_text="Enable the option for customers to add individual add-ons."
    )

                             
    packages_enabled = models.BooleanField(
        default=True,
        help_text="Enable the option for customers to select add-on packages."
    )

                                            
                                     
    minimum_hire_duration_hours = models.PositiveIntegerField(
        default=2,
        help_text="Minimum duration for a hire booking in hours."
    )

                                           
    booking_lead_time_hours = models.PositiveIntegerField(
        default=2,
        help_text="Minimum hours required between booking time and pickup time."
    )

                                    
    grace_period_minutes = models.PositiveIntegerField(default=0, help_text="Grace period after return time before late fees apply.")

                           
    pick_up_start_time = models.TimeField(default=time(9, 0), help_text="Earliest time of day for service pickups (e.g., 09:00)")
    pick_up_end_time = models.TimeField(default=time(17, 0), help_text="Latest time of day for service pickups (e.g., 17:00)")

                          
    return_off_start_time = models.TimeField(default=time(9, 0), help_text="Earliest time of day for service returns (e.g., 09:00)")
    return_end_time = models.TimeField(default=time(17, 0), help_text="Latest time of day for service returns (e.g., 17:00)")


                                                        
    maximum_hire_duration_days = models.IntegerField(default=30, help_text="Maximum number of days for a hire booking")
    hire_confirmation_email_subject = models.CharField(max_length=200, default="Your motorcycle hire booking has been confirmed", help_text="Subject line for hire booking confirmation emails")
    admin_hire_notification_email = models.EmailField(blank=True, null=True, help_text="Email address for hire booking notifications")

                                        
    hire_pricing_strategy = models.CharField(
        max_length=50,
        choices=HIRE_PRICING_STRATEGY_CHOICES,
        default='24_hour_customer_friendly',                                      
        help_text="Defines how multi-day hire prices are calculated."
    )

                                                    
    excess_hours_margin = models.PositiveIntegerField(
        default=2,
        help_text="For '24-Hour Billing with Margin' strategy: number of excess hours allowed before charging for a full day."
    )

    late_fee_per_day = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True, blank=True,
        help_text="Fee charged per full day for late returns (if applicable).")

                          
                                 
    enable_cleaning_fee = models.BooleanField(
        default=False,
        help_text="Enable the option to charge a cleaning fee.")

                                  
    default_cleaning_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True, blank=True,
        help_text="Default amount for a cleaning fee.")

                                 
                                  
    minimum_driver_age = models.PositiveIntegerField(
        default=18, help_text="Minimum age required to be a driver.")

                                           
    young_driver_surcharge_age_limit = models.PositiveIntegerField(
        default=25,
        help_text="Age limit below which a young driver surcharge might apply.")

                                    
    require_driver_license_upload = models.BooleanField(default=False, help_text="Require customers to upload driver license copies during booking.")

                               
                            
    currency_code = models.CharField(max_length=3, default='AUD', help_text="The primary currency code (ISO 4217) for all prices and calculations.")

                      
    currency_symbol = models.CharField(max_length=5, default='$', help_text="Symbol for the currency.")

                                         
                                    
    cancellation_upfront_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund if cancelled this many *full days* or more before pickup time (for upfront payments)."
    )
                                       
    cancellation_upfront_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund if cancelled this many *full days* or more (but less than full refund threshold) before pickup time (for upfront payments)."
    )
                                    
    cancellation_upfront_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=50.00,
        help_text="Percentage of total hire price to refund for partial cancellations (for upfront payments)."
    )
                                       
    cancellation_upfront_minimal_refund_days = models.PositiveIntegerField(
         default=1,
         help_text="Minimal refund percentage applies if cancelled this many *full days* or more (but less than partial refund threshold) before pickup time (for upfront payments)."
    )
                                    
    cancellation_upfront_minimal_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00,
        help_text="Percentage of total hire price to refund for late cancellations (for upfront payments)."
    )

                                         
                                                 
    cancellation_deposit_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund of deposit if cancelled this many *full days* or more before pickup time."
    )
                                                    
    cancellation_deposit_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund of deposit if cancelled this many *full days* or more (but less than full refund threshold) before pickup time."
    )
                                            
    cancellation_deposit_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=50.00,
        help_text="Percentage of deposit to refund for partial cancellations."
    )
                                                    
    cancellation_deposit_minimal_refund_days = models.PositiveIntegerField(
         default=1,
         help_text="Minimal refund percentage applies to deposit if cancelled this many *full days* or more (but less than partial refund threshold) before pickup time."
    )
                                            
    cancellation_deposit_minimal_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00,
        help_text="Percentage of deposit to refund for late cancellations."
    )

                                       
    def save(self, *args, **kwargs):
        if not self.pk and HireSettings.objects.exists():
            existing = HireSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

                                        
    def __str__(self):
        return "Hire Settings"

    class Meta:
        verbose_name = "Hire Settings"
        verbose_name_plural = "Hire Settings"
