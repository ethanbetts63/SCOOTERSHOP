from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import datetime
import stripe
from inventory.models import Motorcycle
from .driver_profile import DriverProfile
from dashboard.models import HireSettings
from payments.models import Payment


STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
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

PAYMENT_METHOD_CHOICES = [
    ('online_full', 'Full Payment Online'),
    ('online_deposit', 'Deposit Payment Online'),
    ('in_store_full', 'Full Payment Store'),
]

class HireBooking(models.Model):
    motorcycle = models.ForeignKey(
        Motorcycle,
        on_delete=models.CASCADE,
        related_name='hire_bookings',
        limit_choices_to={'conditions__name': 'hire'}
    )
    driver_profile = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='hire_bookings'
    )
    package = models.ForeignKey(
        'Package',
        on_delete=models.SET_NULL,
        related_name='hire_bookings',
        null=True, blank=True
    )

    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        related_name='related_hire_booking_payment',
        null=True, blank=True,
        help_text="Link to the associated payment record."
    )

    stripe_payment_intent_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="The ID of the Stripe Payment Intent associated with this booking."
    )

    add_ons = models.ManyToManyField(
        'AddOn',
        through='BookingAddOn',
        related_name='hire_bookings',
        blank=True
    )

    pickup_date = models.DateField(help_text="Pickup date")
    pickup_time = models.TimeField(help_text="Pickup time")
    return_date = models.DateField(help_text="Return date")
    return_time = models.TimeField(help_text="Return time")

    booking_reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_international_booking = models.BooleanField(default=False)

    booked_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booked_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_hire_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_addons_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_package_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, help_text="Method by which the payment was made.")

    currency = models.CharField(
        max_length=3,
        default='AUD',
        help_text="The three-letter ISO currency code for the booking."
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    customer_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hire: {self.motorcycle} ({self.pickup_date} to {self.return_date}) - {self.status}"

    def clean(self):
        super().clean()

        errors = {}
        now = timezone.now()

        pickup_datetime = None
        return_datetime = None

        if self.pickup_date and self.pickup_time:
            pickup_datetime = timezone.make_aware(datetime.datetime.combine(self.pickup_date, self.pickup_time))

        if self.return_date and self.return_time:
            return_datetime = timezone.make_aware(datetime.datetime.combine(self.return_date, self.return_time))

        if pickup_datetime and return_datetime:
            if return_datetime <= pickup_datetime:
                errors['return_date'] = "Return date and time must be after pickup date and time."
                errors['return_time'] = "Return date and time must be after pickup date and time."

        if pickup_datetime:
            try:
                settings = HireSettings.objects.first()
                if settings and settings.booking_lead_time_hours is not None:
                    min_pickup_time = now + datetime.timedelta(hours=settings.booking_lead_time_hours)
                    if pickup_datetime < min_pickup_time:
                        errors['pickup_date'] = f"Pickup must be at least {settings.booking_lead_time_hours} hours from now."
                        errors['pickup_time'] = f"Pickup must be at least {settings.booking_lead_time_hours} hours from now."
            except HireSettings.DoesNotExist:
                pass
            except Exception as e:
                pass


        if self.grand_total is not None and self.grand_total < 0:
            errors['grand_total'] = "Grand total cannot be negative."
        if self.total_hire_price is not None and self.total_hire_price < 0:
            errors['total_hire_price'] = "Total hire price cannot be negative."
        if self.total_addons_price is not None and self.total_addons_price < 0:
            errors['total_addons_price'] = "Total add-ons price cannot be negative."
        if self.total_package_price is not None and self.total_package_price < 0:
            errors['total_package_price'] = "Total package price cannot be negative."
        if self.deposit_amount is not None and self.deposit_amount < 0:
            errors['deposit_amount'] = "Deposit amount cannot be negative."
        if self.amount_paid is not None and self.amount_paid < 0:
            errors['amount_paid'] = "Amount paid cannot be negative."

        if self.payment_status == 'paid' and self.amount_paid != self.grand_total:
            errors['amount_paid'] = "Amount paid must equal grand total when payment status is 'Paid'."
        if self.payment_status == 'deposit_paid':
            if self.deposit_amount is None or self.deposit_amount <= 0:
                errors['deposit_amount'] = "Deposit amount must be set when payment status is 'Deposit Paid'."
            if self.amount_paid != self.deposit_amount:
                errors['amount_paid'] = "Amount paid must equal the deposit amount when payment status is 'Deposit Paid'."
        if self.payment_status == 'unpaid' and self.amount_paid > 0:
            pass

        if self.booked_daily_rate is not None and self.booked_daily_rate < 0:
            errors['booked_daily_rate'] = "Booked daily rate cannot be negative."
        if self.booked_hourly_rate is not None and self.booked_hourly_rate < 0:
            errors['booked_hourly_rate'] = "Booked hourly rate cannot be negative."


        if self.package and not self.package.is_available:
            errors['package'] = f"The selected package '{self.package.name}' is currently not available."

        if self.is_international_booking and self.driver_profile and self.driver_profile.is_australian_resident:
            errors['is_international_booking'] = "Cannot mark as international booking if the driver is an Australian resident."


        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ['pickup_date', 'pickup_time', 'motorcycle']
        verbose_name = "Hire Booking"
        verbose_name_plural = "Hire Bookings"
