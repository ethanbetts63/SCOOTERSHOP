from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import time

class ServiceSettings(models.Model):
    #--
                              
    enable_service_booking = models.BooleanField(default=True, help_text="Globally enable or disable the service booking system.")
    booking_advance_notice = models.IntegerField(default=1, help_text="Minimum number of days notice required for a booking (e.g., 1 for next day).")
    max_visible_slots_per_day = models.IntegerField(default=2, help_text="Maximum number of booking slots to show per day in the calendar.")
    
                         
    allow_anonymous_bookings = models.BooleanField(default=True, help_text="Allow users to book without creating an account.")
    allow_account_bookings = models.BooleanField(default=True, help_text="Allow logged-in users to book.")

                          
    booking_open_days = models.CharField(
        max_length=255, default="Mon,Tue,Wed,Thu,Fri",
        help_text="Comma-separated list of days when bookings are open (e.g., Mon,Tue,Wed,Thu,Fri,Sat,Sun)."
    )
    
    drop_off_start_time = models.TimeField(default=time(9, 0), help_text="The earliest time customers can drop off their motorcycle.")
    drop_off_end_time = models.TimeField(default=time(17, 0), help_text="The latest time customers can drop off their motorcycle.")
    
                                                                                           
    drop_off_spacing_mins = models.IntegerField(default=30, help_text="The minimum interval in minutes between two booking drop offs on the same day.")

                                                                                                    
    max_advance_dropoff_days = models.IntegerField(
        default=0,                                                                                       
        help_text="Maximum number of days in advance a customer can drop off their motorcycle before the service date."
    )

                                                                                               
    latest_same_day_dropoff_time = models.TimeField(
        default=time(12, 0),                             
        help_text="The latest time a customer can drop off their motorcycle if the drop-off date is the same as the service date."
    )

                                                 
    allow_after_hours_dropoff = models.BooleanField(
        default=False,
        help_text="Allow customers to drop off their motorcycle outside of standard opening hours (e.g., using a secure drop box)."
    )
    after_hours_dropoff_disclaimer = models.TextField(
        blank=True,
        help_text="Important disclaimer text displayed to users when after-hours drop-off is selected, outlining risks/conditions."
    )
                            

    enable_service_brands = models.BooleanField(default=True, help_text="Enable filtering or special handling by motorcycle brand.")
    other_brand_policy_text = models.TextField(
        blank=True,
        help_text="Policy text displayed to users when booking for an 'Other' brand motorcycle (e.g., regarding review, potential rejection, and refund policy)."
    )

                      
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

                     
    enable_online_full_payment = models.BooleanField(default=False, help_text="Allow customers to pay the full amount online.")
    enable_online_deposit = models.BooleanField(default=True, help_text="Allow customers to pay the deposit amount online (if deposits are enabled).")
    enable_instore_full_payment = models.BooleanField(default=True, help_text="Allow customers to opt for paying the full amount in-store.")
    
              
    currency_code = models.CharField(max_length=3, default='AUD', help_text="Currency code (e.g., AUD, USD).")
    currency_symbol = models.CharField(max_length=5, default='$', help_text="Currency symbol (e.g., $).")

                                                                         
                                                                    
                                                 

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

                                        
        if self.drop_off_spacing_mins is not None and (self.drop_off_spacing_mins <= 0 or self.drop_off_spacing_mins > 60):
            errors['drop_off_spacing_mins'] = ["Drop-off spacing must be a positive integer, typically between 1 and 60 minutes."]

                                           
        if self.max_advance_dropoff_days is not None and self.max_advance_dropoff_days < 0:
            errors['max_advance_dropoff_days'] = ["Maximum advance drop-off days cannot be negative."]
        
                                                                                                   
        if latest_same_day_dropoff and (latest_same_day_dropoff < start_time or latest_same_day_dropoff > end_time):
            errors['latest_same_day_dropoff_time'] = [f"Latest same-day drop-off time must be between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}, inclusive."]

                                                                                                       
                                                                                       
        if self.deposit_percentage is not None and not (Decimal('0.00') <= self.deposit_percentage <= Decimal('100.00')):
            errors['deposit_percentage'] = ["Ensure deposit percentage is between 0.00% and 100.00%."]


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
