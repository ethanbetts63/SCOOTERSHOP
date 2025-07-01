                                  

import uuid
from django.db import models
from django.utils import timezone
from inventory.models import Motorcycle
from .driver_profile import DriverProfile
from .hire_addon import AddOn
from .hire_packages import Package


class TempHireBooking(models.Model):
    """
    Temporarily stores booking details as the user progresses through the steps.
    Data is copied to HireBooking upon successful completion.
    """
                                                                  
    session_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
                                                               
                                      
                                                                                                          

                                                    
                                   
    pickup_date = models.DateField(null=True, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    return_time = models.TimeField(null=True, blank=True)
    has_motorcycle_license = models.BooleanField(default=False)                            

                                 
    motorcycle = models.ForeignKey(
        Motorcycle,
        on_delete=models.SET_NULL,                                                 
        related_name='temp_hire_bookings',
        null=True, blank=True
    )

                                 
                                                                   
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,               
        related_name='temp_hire_bookings',
        null=True, blank=True
    )

                            
    driver_profile = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,               
        related_name='temp_hire_bookings',
        null=True, blank=True
    )
                                                                                     
    is_international_booking = models.BooleanField(default=False)

                                
    PAYMENT_METHOD_CHOICES = [
        ('online_full', 'Full Payment Online'),
        ('online_deposit', 'Deposit Payment Online'),
        ('in_store_full', 'Full Payment Store'),
    ]
    payment_option = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="The selected payment option for this booking."
    )

                                        
                                                                                
    booked_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    total_hire_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,                                                      
        help_text="Calculated total price for the motorcycle hire duration only."
    )
    total_addons_price = models.DecimalField(
         max_digits=10, decimal_places=2,
         default=0,
         null=True, blank=True,
         help_text="Calculated total price for selected add-ons."
    )
                                                            
    total_package_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    grand_total = models.DecimalField(
         max_digits=10, decimal_places=2,
         null=True, blank=True,                   
         help_text="Sum of total_hire_price, total_addons_price, and total_package_price."
    )
                                                        
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="The deposit amount required for the booking."
    )
                                                 
    currency = models.CharField(
        max_length=3,
        default='AUD', 
        help_text="The three-letter ISO currency code for the booking."
    )


                        
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        motorcycle_str = self.motorcycle.model if self.motorcycle else 'No bike selected'
        date_range = f"({self.pickup_date} to {self.return_date})" if self.pickup_date and self.return_date else "(Dates not set)"
        return f"Temp Booking ({str(self.session_uuid)[:8]}): {motorcycle_str} {date_range}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Temporary Hire Booking"
        verbose_name_plural = "Temporary Hire Bookings"

