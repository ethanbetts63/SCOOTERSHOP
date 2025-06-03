from django.db import models
import uuid
from payments.models import Payment
from service.models import ServiceProfile, ServiceType, CustomerMotorcycle

class ServiceBooking(models.Model):
    """
    Full model to incrementally store booking data during the multi-step user flow.
    """
    # Choices for payment method
    PAYMENT_METHOD_CHOICES = [
        ('online_full', 'Full Payment Online'),
        ('online_deposit', 'Deposit Payment Online'),
        ('in_store_full', 'Full Payment Store'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('deposit_paid', 'Deposit Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded'),
    ]
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('declined', 'Declined by Admin'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
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
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        related_name='related_service_booking_payment', 
        null=True, blank=True, 
        help_text="Link to the associated payment record."
    )
    calculated_total = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, help_text="Method by which the payment was made.")

    # Currency of the booking (NEW FIELD)
    currency = models.CharField(
        max_length=3,
        default='AUD',
        help_text="The three-letter ISO currency code for the booking."
    )
    # Add a field to store the Stripe Payment Intent ID directly
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True, 
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent associated with this booking."
    )
    
    dropoff_date = models.DateField(help_text="Requested date for the service.")
    dropoff_time = models.TimeField(help_text="Requested drop-off time for the service.")
    estimated_pickup_date = models.DateField(null=True, blank=True, help_text="Estimated pickup date set by admin.")


    booking_status = models.CharField(max_length=30, choices=BOOKING_STATUS_CHOICES, default='PENDING_CONFIRMATION')
    customer_notes = models.TextField(blank=True, null=True, help_text="Any additional notes from the customer.")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"SERVICE-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Temp Booking {self.uuid} for {self.service_profile.name} on {self.appointment_date}"

    class Meta:
        verbose_name = "Temporary Service Booking"
        verbose_name_plural = "Temporary Service Bookings"
        ordering = ['-created_at']