# SCOOTER_SHOP/service/models.py

from django.db import models
from datetime import timedelta, time
import uuid
from users.models import User
from datetime import time
import datetime
from inventory.models import Motorcycle


# Model for customers' personal motorcycles being serviced
class CustomerMotorcycle(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_motorcycles')
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    vin_number = models.CharField(max_length=50, blank=True, null=True, help_text="(OPTIONAL) Vehicle Idenitification Number")
    engine_number = models.CharField(max_length=50, blank=True, null=True)
    rego = models.CharField(max_length=20, default='') 
    date_added = models.DateTimeField(auto_now_add=True)
    odometer = models.IntegerField(default=0)
    transmission = models.CharField(
        max_length=20,
        choices=Motorcycle.TRANSMISSION_CHOICES,
        blank=True,
        null=True,
        help_text="(OPTIONAL) Motorcycle transmission type"
    )

    # String representation of the CustomerMotorcycle instance
    def __str__(self):
        return f"{self.year} {self.make} {self.model} (owned by {self.owner.get_full_name() or self.owner.username})"

# Model defining types of service offered
class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    estimated_duration = models.DurationField(help_text="Estimated time to complete this service")
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True, help_text="Whether this service is currently offered")
    image = models.FileField(upload_to='service_types/', null=True, blank=True, help_text="Icon image for this service type")

    # String representation of the ServiceType instance
    def __str__(self):
        return self.name

# Model for service appointments
class ServiceBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    CONTACT_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
    ]

    customer = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='service_bookings', null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True, help_text="For anonymous bookings")
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)

    vehicle = models.ForeignKey(
        CustomerMotorcycle,
        on_delete=models.SET_NULL,
        related_name='service_bookings',
        null=True,
        blank=True,
        help_text="Customer's motorcycle to be serviced (if linked to an account)"
    )

    anon_vehicle_make = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle Make for anonymous bookings")
    anon_vehicle_model = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle Model for anonymous bookings")
    anon_vehicle_year = models.IntegerField(blank=True, null=True, help_text="Vehicle Year for anonymous bookings")
    anon_vehicle_rego = models.CharField(max_length=20, blank=True, null=True, help_text="Vehicle Registration for anonymous bookings")
    anon_vehicle_vin_number = models.CharField(max_length=50, blank=True, null=True, help_text="Vehicle VIN for anonymous bookings")
    anon_vehicle_odometer = models.IntegerField(blank=True, null=True, help_text="Vehicle Odometer for anonymous bookings")
    anon_vehicle_transmission = models.CharField(
        max_length=20,
        choices=Motorcycle.TRANSMISSION_CHOICES,
        blank=True,
        null=True,
        help_text="Vehicle Transmission for anonymous bookings"
    )
    anon_engine_number = models.CharField(max_length=50, blank=True, null=True, help_text="Engine Number for anonymous bookings")

    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name='bookings')
    appointment_date = models.DateField(help_text="Date of the service appointment", default=datetime.date.today)
    drop_off_time = models.TimeField(help_text="Scheduled drop-off time", default=time(9, 0))
    pickup_date = models.DateField(blank=True, null=True, help_text="Estimated or actual pickup date")
    customer_notes = models.TextField(blank=True, null=True, help_text="Notes from the customer")
    mechanic_notes = models.TextField(blank=True, null=True, help_text="Notes from the mechanic")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)

    parts_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # String representation of the ServiceBooking instance
    def __str__(self):
        return f"Booking {self.booking_reference or self.pk} for {self.customer_name or self.customer} on {self.appointment_date}"

    class Meta:
        ordering = ['appointment_date', 'drop_off_time']