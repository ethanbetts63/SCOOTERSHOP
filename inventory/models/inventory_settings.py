from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import time


class InventorySettings(models.Model):
    enable_depositless_viewing = models.BooleanField(
        default=True,
        help_text="Allow customers to submit an appointment request for a motorcycle viewing without requiring a deposit.",
    )
    enable_reservation_by_deposit = models.BooleanField(
        default=True,
        help_text="Allow customers to reserve a motorcycle by paying a deposit.",
    )

    enable_viewing_for_enquiry = models.BooleanField(
        default=True,
        help_text="Allow customers to request a specific viewing/appointment date/time within the deposit-less enquiry flow.",
    )

    enable_sales_enquiries = models.BooleanField(
        default=True,
        help_text="Allow customers to make a general enquiry about a motorcycle.",
    )

    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text="The fixed amount required for a motorcycle reservation deposit.",
    )
    deposit_lifespan_days = models.IntegerField(
        default=5,
        help_text="Number of days a deposit holds a motorcycle reservation. After this period, the reservation may expire.",
    )

    enable_sales_new_bikes = models.BooleanField(
        default=True,
        help_text="Enable the sales process for 'New' motorcycles in the inventory.",
    )
    enable_sales_used_bikes = models.BooleanField(
        default=True,
        help_text="Enable the sales process for 'Used' and 'Demo' motorcycles in the inventory.",
    )

    require_drivers_license = models.BooleanField(
        default=False,
        help_text="Require customers to provide driver's license details.",
    )

    require_address_info = models.BooleanField(
        default=False, help_text="Require customers to provide address details."
    )

    sales_booking_open_days = models.CharField(
        max_length=255,
        default="Mon,Tue,Wed,Thu,Fri,Sat",
        help_text="Comma-separated list of days when sales appointments (test drives, viewings) are open.",
    )
    sales_appointment_start_time = models.TimeField(
        default=time(9, 0),
        help_text="The earliest time a sales appointment can be scheduled.",
    )
    sales_appointment_end_time = models.TimeField(
        default=time(17, 0),
        help_text="The latest time a sales appointment can be scheduled.",
    )
    sales_appointment_spacing_mins = models.IntegerField(
        default=30,
        help_text="The minimum interval in minutes between two sales appointments on the same day.",
    )
    max_advance_booking_days = models.IntegerField(
        default=90,
        help_text="Maximum number of days in advance a customer can book a sales appointment.",
    )
    min_advance_booking_hours = models.IntegerField(
        default=24,
        help_text="Minimum number of hours notice required for a sales appointment.",
    )

    send_sales_booking_to_mechanic_desk = models.BooleanField(
        default=False,
        help_text="Automatically send sales booking details to the mechanic's desk upon confirmation.",
    )

    currency_code = models.CharField(
        max_length=3,
        default="AUD",
        help_text="The three-letter ISO currency code for sales transactions (e.g., AUD, USD).",
    )
    currency_symbol = models.CharField(
        max_length=5,
        default="$",
        help_text="The currency symbol for sales transactions (e.g., $).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Settings"
        verbose_name_plural = "Inventory Settings"

    def __str__(self):
        return "Inventory Settings"

    def clean(self):
        super().clean()
        errors = {}

        if self.deposit_amount is not None and self.deposit_amount < Decimal("0.00"):
            errors["deposit_amount"] = ["Deposit amount cannot be negative."]

        if self.deposit_lifespan_days is not None and self.deposit_lifespan_days < 0:
            errors["deposit_lifespan_days"] = [
                "Deposit lifespan days cannot be negative."
            ]

        if self.sales_appointment_start_time and self.sales_appointment_end_time:
            if self.sales_appointment_start_time >= self.sales_appointment_end_time:
                errors["sales_appointment_start_time"] = [
                    "Start time must be earlier than end time."
                ]
                errors["sales_appointment_end_time"] = [
                    "End time must be later than start time."
                ]

        if (
            self.sales_appointment_spacing_mins is not None
            and self.sales_appointment_spacing_mins <= 0
        ):
            errors["sales_appointment_spacing_mins"] = [
                "Appointment spacing must be a positive integer."
            ]

        if (
            self.max_advance_booking_days is not None
            and self.max_advance_booking_days < 0
        ):
            errors["max_advance_booking_days"] = [
                "Maximum advance booking days cannot be negative."
            ]

        if (
            self.min_advance_booking_hours is not None
            and self.min_advance_booking_hours < 0
        ):
            errors["min_advance_booking_hours"] = [
                "Minimum advance booking hours cannot be negative."
            ]

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

        if not self.pk and InventorySettings.objects.exists():
            raise ValidationError(
                "Only one instance of InventorySettings can be created. Please edit the existing one."
            )
        super().save(*args, **kwargs)
