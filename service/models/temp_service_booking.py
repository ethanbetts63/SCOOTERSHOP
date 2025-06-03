from django.db import models
import uuid
from service.models import ServiceProfile, ServiceType, CustomerMotorcycle

class TempServiceBooking(models.Model):
    """
    Temporary model to incrementally store booking data during the multi-step user flow.
    """
    # Choices for payment method
    PAYMENT_METHOD_CHOICES = [
        ('online_full', 'Full Payment Online'),
        ('online_deposit', 'Deposit Payment Online'),
        ('in_store_full', 'Full Payment Store'),
    ]

    session_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Unique identifier for retrieving the temporary booking.")
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT, # Don't allow deleting a ServiceType if temp bookings exist for it.
                                 # Consider models.SET_NULL or specific handling if ServiceType can be deleted.
        related_name='temp_service_bookings',
        help_text="Selected service type."
    )
    service_profile = models.ForeignKey(
        ServiceProfile,
        on_delete=models.CASCADE, # If profile is deleted, temp booking is also deleted.
        related_name='temp_service_bookings',
        help_text="The customer profile associated with this temporary booking."
    )
    customer_motorcycle = models.ForeignKey(
        CustomerMotorcycle,
        on_delete=models.SET_NULL,           
        null=True, blank=True, 
        related_name='temp_service_bookings',
        help_text="Chosen motorcycle for this service (set in a later step)."
    )
    payment_option = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="The selected payment option for this booking."
    )
    
    dropoff_date = models.DateField(help_text="Requested date for the service.")
    dropoff_time = models.TimeField(help_text="Requested drop-off time for the service.")
    estimated_pickup_date = models.DateField(null=True, blank=True, help_text="Estimated pickup date set by admin.")

    customer_notes = models.TextField(blank=True, null=True, help_text="Any additional notes from the customer.")
    calculated_deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, # Deposit might not be applicable or calculated yet.
        help_text="Calculated deposit amount, if applicable."
    )
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Temp Booking {self.uuid} for {self.service_profile.name} on {self.appointment_date}"

    class Meta:
        verbose_name = "Temporary Service Booking"
        verbose_name_plural = "Temporary Service Bookings"
        ordering = ['-created_at']