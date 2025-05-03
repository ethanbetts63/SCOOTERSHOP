# SCOOTER_SHOP/hire/models.py

from django.db import models
import uuid
# Need to import User from users app and Motorcycle from inventory app
from users.models import User
from inventory.models import Motorcycle


# Model for motorcycle hire bookings
class HireBooking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('deposit_paid', 'Deposit Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded'),
    ]

    motorcycle = models.ForeignKey(
        Motorcycle, # Link to the Motorcycle model in the inventory app
        on_delete=models.CASCADE,
        related_name='hire_bookings',
        limit_choices_to={'conditions__name': 'hire'}
    )

    customer = models.ForeignKey(
        User, # Use the User model from the users app
        on_delete=models.SET_NULL,
        related_name='hire_bookings',
        null=True,
        blank=True
    )

    pickup_datetime = models.DateTimeField(help_text="Pickup date and time")
    dropoff_datetime = models.DateTimeField(help_text="Dropoff date and time")

    # Booking financial details
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_weekly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_monthly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')

    # Booking metadata
    booking_reference = models.CharField(max_length=20, unique=True, blank=True)
    customer_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hire: {self.motorcycle} ({self.pickup_datetime.strftime('%Y-%m-%d')} to {self.dropoff_datetime.strftime('%Y-%m-%d')}) - {self.status}"

    class Meta:
        ordering = ['pickup_datetime', 'motorcycle']