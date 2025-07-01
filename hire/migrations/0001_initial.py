                                             

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AddOn",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Name of the add-on.", max_length=100),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Description of the add-on.", null=True
                    ),
                ),
                (
                    "hourly_cost",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Cost of the add-on per item per hour.",
                        max_digits=8,
                    ),
                ),
                (
                    "daily_cost",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Cost of the add-on per item per day.",
                        max_digits=8,
                    ),
                ),
                (
                    "min_quantity",
                    models.PositiveIntegerField(
                        default=1, help_text="Minimum quantity allowed for this add-on."
                    ),
                ),
                (
                    "max_quantity",
                    models.PositiveIntegerField(
                        default=1, help_text="Maximum quantity allowed for this add-on."
                    ),
                ),
                (
                    "is_available",
                    models.BooleanField(
                        default=True,
                        help_text="Is this add-on currently available for booking?",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Hire Add-On",
                "verbose_name_plural": "Hire Add-Ons",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="DriverProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        help_text="Phone number of the driver.", max_length=20
                    ),
                ),
                (
                    "address_line_1",
                    models.CharField(
                        help_text="Address line 1 of the driver.", max_length=100
                    ),
                ),
                (
                    "address_line_2",
                    models.CharField(
                        blank=True,
                        help_text="Address line 2 of the driver.",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "city",
                    models.CharField(help_text="City of the driver.", max_length=50),
                ),
                (
                    "state",
                    models.CharField(
                        blank=True,
                        help_text="State of the driver.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "post_code",
                    models.CharField(
                        blank=True,
                        help_text="Postal code of the driver.",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "country",
                    models.CharField(help_text="Country of the driver.", max_length=50),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Full name of the driver.", max_length=100
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        help_text="Email address of the driver.", max_length=254
                    ),
                ),
                (
                    "date_of_birth",
                    models.DateField(help_text="Date of birth of the driver."),
                ),
                (
                    "is_australian_resident",
                    models.BooleanField(
                        default=False, help_text="Is the driver an Australian resident?"
                    ),
                ),
                (
                    "license_number",
                    models.CharField(
                        blank=True,
                        help_text="Driver's license number.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "international_license_issuing_country",
                    models.CharField(
                        blank=True,
                        help_text="Country that issued the International Driver's License.",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "license_expiry_date",
                    models.DateField(
                        blank=True, help_text="Expiry date of the license.", null=True
                    ),
                ),
                (
                    "international_license_expiry_date",
                    models.DateField(
                        blank=True,
                        help_text="Expiry date of the International Driver's License.",
                        null=True,
                    ),
                ),
                (
                    "id_image",
                    models.FileField(
                        blank=True,
                        help_text="Image of the driver's ID.",
                        null=True,
                        upload_to="user_ids/",
                    ),
                ),
                (
                    "international_id_image",
                    models.FileField(
                        blank=True,
                        help_text="Image of the driver's international ID.",
                        null=True,
                        upload_to="user_ids/international/",
                    ),
                ),
                (
                    "license_photo",
                    models.FileField(
                        blank=True,
                        help_text="Upload of the driver's primary license (Australian domestic for residents).",
                        null=True,
                        upload_to="driver_profiles/licenses/",
                    ),
                ),
                (
                    "international_license_photo",
                    models.FileField(
                        blank=True,
                        help_text="Upload of the International Driver's License (required for foreigners).",
                        null=True,
                        upload_to="driver_profiles/international_licenses/",
                    ),
                ),
                (
                    "passport_photo",
                    models.FileField(
                        blank=True,
                        help_text="Upload of the driver's passport (required for foreigners).",
                        null=True,
                        upload_to="driver_profiles/passports/",
                    ),
                ),
                (
                    "passport_number",
                    models.CharField(
                        blank=True,
                        help_text="Passport number.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "passport_expiry_date",
                    models.DateField(
                        blank=True, help_text="Passport expiry date.", null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Driver Profile",
                "verbose_name_plural": "Driver Profiles",
                "ordering": ["name", "email"],
            },
        ),
        migrations.CreateModel(
            name="HireBooking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        help_text="The ID of the Stripe Payment Intent associated with this booking.",
                        max_length=100,
                        null=True,
                        unique=True,
                    ),
                ),
                ("pickup_date", models.DateField(help_text="Pickup date")),
                ("pickup_time", models.TimeField(help_text="Pickup time")),
                ("return_date", models.DateField(help_text="Return date")),
                ("return_time", models.TimeField(help_text="Return time")),
                (
                    "booking_reference",
                    models.CharField(blank=True, max_length=20, null=True, unique=True),
                ),
                ("is_international_booking", models.BooleanField(default=False)),
                (
                    "booked_hourly_rate",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "booked_daily_rate",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "total_hire_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "total_addons_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                (
                    "total_package_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("grand_total", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "deposit_amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=8),
                ),
                (
                    "amount_paid",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                (
                    "payment_status",
                    models.CharField(
                        choices=[
                            ("unpaid", "Unpaid"),
                            ("deposit_paid", "Deposit Paid"),
                            ("paid", "Fully Paid"),
                            ("refunded", "Refunded"),
                        ],
                        default="unpaid",
                        max_length=20,
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("online_full", "Full Payment Online"),
                            ("online_deposit", "Deposit Payment Online"),
                            ("in_store_full", "Full Payment Store"),
                        ],
                        help_text="Method by which the payment was made.",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="AUD",
                        help_text="The three-letter ISO currency code for the booking.",
                        max_length=3,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("no_show", "No Show"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("customer_notes", models.TextField(blank=True, null=True)),
                ("internal_notes", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Hire Booking",
                "verbose_name_plural": "Hire Bookings",
                "ordering": ["pickup_date", "pickup_time", "motorcycle"],
            },
        ),
        migrations.CreateModel(
            name="Package",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Name of the package.", max_length=100),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Description of the package.", null=True
                    ),
                ),
                (
                    "hourly_cost",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="The current price of this package bundle per hour.",
                        max_digits=10,
                    ),
                ),
                (
                    "daily_cost",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="The current price of this package bundle per day.",
                        max_digits=10,
                    ),
                ),
                (
                    "is_available",
                    models.BooleanField(
                        default=True,
                        help_text="Is this package currently available for booking?",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Hire Package",
                "verbose_name_plural": "Hire Packages",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="TempBookingAddOn",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1)),
                (
                    "booked_addon_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Total price for this quantity of add-on at the time of selection.",
                        max_digits=8,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Temporary Booking Add-On",
                "verbose_name_plural": "Temporary Booking Add-Ons",
            },
        ),
        migrations.CreateModel(
            name="TempHireBooking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("session_uuid", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("pickup_date", models.DateField(blank=True, null=True)),
                ("pickup_time", models.TimeField(blank=True, null=True)),
                ("return_date", models.DateField(blank=True, null=True)),
                ("return_time", models.TimeField(blank=True, null=True)),
                ("has_motorcycle_license", models.BooleanField(default=False)),
                ("is_international_booking", models.BooleanField(default=False)),
                (
                    "payment_option",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("online_full", "Full Payment Online"),
                            ("online_deposit", "Deposit Payment Online"),
                            ("in_store_full", "Full Payment Store"),
                        ],
                        help_text="The selected payment option for this booking.",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "booked_hourly_rate",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "booked_daily_rate",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "total_hire_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Calculated total price for the motorcycle hire duration only.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "total_addons_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=0,
                        help_text="Calculated total price for selected add-ons.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "total_package_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "grand_total",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Sum of total_hire_price, total_addons_price, and total_package_price.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "deposit_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="The deposit amount required for the booking.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="AUD",
                        help_text="The three-letter ISO currency code for the booking.",
                        max_length=3,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Temporary Hire Booking",
                "verbose_name_plural": "Temporary Hire Bookings",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="BookingAddOn",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="The quantity of this add-on included in the booking.",
                    ),
                ),
                (
                    "booked_addon_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Total price for this quantity of add-on at the time of booking.",
                        max_digits=8,
                    ),
                ),
                (
                    "addon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addon_bookings",
                        to="hire.addon",
                    ),
                ),
            ],
        ),
    ]
