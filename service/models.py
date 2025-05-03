# SCOOTER_SHOP/service/models.py

from django.db import models
from datetime import timedelta, time
import uuid
# Need to import the User model from the users app
from users.models import User
# Need to import Motorcycle from inventory to reference choices
from inventory.models import Motorcycle


# Model for customers' personal motorcycles being serviced
class CustomerMotorcycle(models.Model):
    # Use the User model from the users app
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_motorcycles')
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    vin_number = models.CharField(max_length=50, blank=True, null=True)
    engine_number = models.CharField(max_length=50, blank=True, null=True)
    rego = models.CharField(max_length=20, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    odometer = models.IntegerField(null=True, blank=True)
    transmission = models.CharField(
        max_length=20,
        choices=Motorcycle.TRANSMISSION_CHOICES, # Reference choices from Motorcycle
        blank=True,
        null=True,
        help_text="Customer motorcycle transmission type"
    )

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

    # Customer details (can be linked to user or anonymous)
    # Use the User model from the users app
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='service_bookings', null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True, help_text="For anonymous bookings")
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)

    # Added preferred contact method
    preferred_contact = models.CharField(max_length=10, choices=CONTACT_CHOICES, blank=True, null=True)

    # Vehicle details (link to CustomerMotorcycle for logged-in users or store details directly for anonymous)
    vehicle = models.ForeignKey(
        CustomerMotorcycle, # Link to the CustomerMotorcycle model in this app
        on_delete=models.SET_NULL,
        related_name='service_bookings',
        null=True,
        blank=True,
        help_text="Customer's motorcycle to be serviced (if linked to an account)"
    )

    # Added fields for anonymous vehicle details
    anon_vehicle_make = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle Make for anonymous bookings")
    anon_vehicle_model = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle Model for anonymous bookings")
    anon_vehicle_year = models.IntegerField(blank=True, null=True, help_text="Vehicle Year for anonymous bookings")
    anon_vehicle_rego = models.CharField(max_length=20, blank=True, null=True, help_text="Vehicle Registration for anonymous bookings")
    anon_vehicle_odometer = models.IntegerField(blank=True, null=True, help_text="Vehicle Odometer for anonymous bookings")
    anon_vehicle_transmission = models.CharField(
        max_length=20,
        choices=Motorcycle.TRANSMISSION_CHOICES, # Reference choices from Motorcycle in inventory app
        blank=True,
        null=True,
        help_text="Vehicle Transmission for anonymous bookings"
    )

    # Service details
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name='bookings')
    appointment_datetime = models.DateTimeField()
    customer_notes = models.TextField(blank=True, null=True, help_text="Notes from the customer")
    mechanic_notes = models.TextField(blank=True, null=True, help_text="Notes from the mechanic")

    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Cost breakdown
    parts_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate booking reference if not provided
        if not self.booking_reference:
            self.booking_reference = f"SRV-{uuid.uuid4().hex[:8].upper()}"

        # Update total cost if parts and labor are provided
        if self.parts_cost is not None and self.labor_cost is not None:
            self.total_cost = self.parts_cost + self.labor_cost
        elif self.parts_cost is not None: # Handle only parts cost provided
             self.total_cost = self.parts_cost
        elif self.labor_cost is not None: # Handle only labor cost provided
             self.total_cost = self.labor_cost
        else: # Ensure total_cost is None if both parts and labor are None
             self.total_cost = None

        super().save(*args, **kwargs)

    def __str__(self):
        customer_display = self.customer.get_full_name() if self.customer else self.customer_name
        vehicle_display = ""
        if self.vehicle:
            vehicle_display = f" for {self.vehicle}"
        elif self.anon_vehicle_make and self.anon_vehicle_model:
             vehicle_display = f" for {self.anon_vehicle_year or ''} {self.anon_vehicle_make} {self.anon_vehicle_model}"

        return f"Service: {self.service_type} for {customer_display}{vehicle_display} - {self.appointment_datetime.strftime('%Y-%m-%d %H:%M')} ({self.status})"