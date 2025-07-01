from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import re                                       

                                                                     
                                
                                                                                
                                                                                    
try:
    from users.models import User
except ImportError:
                                                                                       
    User = settings.AUTH_USER_MODEL 

class ServiceProfile(models.Model):
    """
    Stores customer contact and identity details for service bookings.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='service_profile',
        null=True, blank=True
    )

                         
    name = models.CharField(max_length=100, blank=False, null=False, help_text="Full name of the customer.")
    email = models.EmailField(blank=False, null=False, help_text="Email address of the customer.")
    phone_number = models.CharField(max_length=20, blank=False, null=False, help_text="Phone number of the customer.")
    
                         
    address_line_1 = models.CharField(max_length=100, blank=False, null=False, help_text="Address line 1.")
    address_line_2 = models.CharField(max_length=100, blank=True, null=True, help_text="Address line 2.")
    city = models.CharField(max_length=50, blank=False, null=False, help_text="City.")
    state = models.CharField(max_length=50, blank=True, null=True, help_text="State/Province.")                               
    post_code = models.CharField(max_length=20, blank=False, null=False, help_text="Postal code.")                 
    country = models.CharField(max_length=50, blank=False, null=False, help_text="Country.")

                
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Profile for {self.user.get_username()} ({self.name})"
        return f"Profile for {self.name} ({self.email})"

    def clean(self):
        """
        Custom validation for the ServiceProfile model.
        """
        super().clean()
        if self.phone_number:
                                                           
            cleaned_phone_number = self.phone_number.replace(' ', '').replace('-', '')
            if not re.fullmatch(r'^\+?\d+$', cleaned_phone_number):
                raise ValidationError({'phone_number': "Phone number must contain only digits, spaces, hyphens, and an optional leading '+'. "
                                                       "Example: '+61412345678' or '0412 345 678'."})
        
        if self.user:
            if self.email and self.user.email and self.email != self.user.email:
                pass                                                                  

    class Meta:
        verbose_name = "Service Customer Profile"
        verbose_name_plural = "Service Customer Profiles"
