import datetime
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlockedServiceDate",
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
                    "start_date",
                    models.DateField(help_text="The start date of the blocked period."),
                ),
                (
                    "end_date",
                    models.DateField(
                        help_text="The end date of the blocked period (inclusive)."
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        help_text="Optional description for the blocked period.",
                        max_length=255,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Blocked Service Date",
                "verbose_name_plural": "Blocked Service Dates",
                "ordering": ["start_date"],
            },
        ),
        migrations.CreateModel(
            name="CustomerMotorcycle",
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
                    "brand",
                    models.CharField(
                        help_text="Brand of the motorcycle (e.g., Honda, Yamaha, or 'Other').",
                        max_length=100,
                    ),
                ),
                (
                    "model",
                    models.CharField(
                        help_text="Model year or specific model identifier.",
                        max_length=100,
                    ),
                ),
                (
                    "year",
                    models.PositiveIntegerField(
                        help_text="Manufacturing year of the motorcycle."
                    ),
                ),
                (
                    "rego",
                    models.CharField(
                        help_text="Registration number (license plate).", max_length=20
                    ),
                ),
                (
                    "odometer",
                    models.PositiveIntegerField(help_text="Odometer reading in km."),
                ),
                (
                    "transmission",
                    models.CharField(
                        choices=[
                            ("MANUAL", "Manual"),
                            ("AUTOMATIC", "Automatic"),
                            ("SEMI_AUTO", "Semi-Automatic"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "engine_size",
                    models.CharField(
                        help_text="Engine displacement (e.g., 250cc, 1000cc).",
                        max_length=50,
                    ),
                ),
                (
                    "vin_number",
                    models.CharField(
                        blank=True,
                        help_text="(optional) Vehicle Identification Number.",
                        max_length=17,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "engine_number",
                    models.CharField(
                        blank=True,
                        help_text="(optional) Engine serial number.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="(optional) Image of the motorcycle.",
                        null=True,
                        upload_to="motorcycle_images/",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Customer Motorcycle",
                "verbose_name_plural": "Customer Motorcycles",
            },
        ),
        migrations.CreateModel(
            name="ServiceBrand",
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
                    models.CharField(
                        help_text="Name of the service brand (e.g., 'Yamaha', 'Vespa').",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Optional image for this brand.",
                        null=True,
                        upload_to="brands/",
                    ),
                ),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Service Brand",
                "verbose_name_plural": "Service Brands",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="ServiceProfile",
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
                    models.CharField(
                        help_text="Full name of the customer.", max_length=100
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        help_text="Email address of the customer.", max_length=254
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        help_text="Phone number of the customer.", max_length=20
                    ),
                ),
                (
                    "address_line_1",
                    models.CharField(help_text="Address line 1.", max_length=100),
                ),
                (
                    "address_line_2",
                    models.CharField(
                        blank=True,
                        help_text="Address line 2.",
                        max_length=100,
                        null=True,
                    ),
                ),
                ("city", models.CharField(help_text="City.", max_length=50)),
                (
                    "state",
                    models.CharField(
                        blank=True,
                        help_text="State/Province.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "post_code",
                    models.CharField(help_text="Postal code.", max_length=20),
                ),
                ("country", models.CharField(help_text="Country.", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Service Customer Profile",
                "verbose_name_plural": "Service Customer Profiles",
            },
        ),
        migrations.CreateModel(
            name="ServiceSettings",
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
                    "enable_service_booking",
                    models.BooleanField(
                        default=True,
                        help_text="Globally enable or disable the service booking system.",
                    ),
                ),
                (
                    "booking_advance_notice",
                    models.IntegerField(
                        default=1,
                        help_text="Minimum number of days notice required for a booking (e.g., 1 for next day).",
                    ),
                ),
                (
                    "max_visible_slots_per_day",
                    models.IntegerField(
                        default=2,
                        help_text="Maximum number of booking slots to show per day in the calendar.",
                    ),
                ),
                (
                    "booking_open_days",
                    models.CharField(
                        default="Mon,Tue,Wed,Thu,Fri",
                        help_text="Comma-separated list of days when bookings are open (e.g., Mon,Tue,Wed,Thu,Fri,Sat,Sun).",
                        max_length=255,
                    ),
                ),
                (
                    "drop_off_start_time",
                    models.TimeField(
                        default=datetime.time(9, 0),
                        help_text="The earliest time customers can drop off their motorcycle.",
                    ),
                ),
                (
                    "drop_off_end_time",
                    models.TimeField(
                        default=datetime.time(17, 0),
                        help_text="The latest time customers can drop off their motorcycle.",
                    ),
                ),
                (
                    "drop_off_spacing_mins",
                    models.IntegerField(
                        default=30,
                        help_text="The minimum interval in minutes between two booking drop offs on the same day.",
                    ),
                ),
                (
                    "max_advance_dropoff_days",
                    models.IntegerField(
                        default=0,
                        help_text="Maximum number of days in advance a customer can drop off their motorcycle before the service date.",
                    ),
                ),
                (
                    "latest_same_day_dropoff_time",
                    models.TimeField(
                        default=datetime.time(12, 0),
                        help_text="The latest time a customer can drop off their motorcycle if the drop-off date is the same as the service date.",
                    ),
                ),
                (
                    "allow_after_hours_dropoff",
                    models.BooleanField(
                        default=False,
                        help_text="Allow customers to drop off their motorcycle outside of standard opening hours (e.g., using a secure drop box).",
                    ),
                ),
                (
                    "after_hours_dropoff_disclaimer",
                    models.TextField(
                        blank=True,
                        help_text="Important disclaimer text displayed to users when after-hours drop-off is selected, outlining risks/conditions.",
                    ),
                ),

                (
                    "enable_deposit",
                    models.BooleanField(
                        default=False,
                        help_text="Enable deposit requirement for bookings.",
                    ),
                ),
                (
                    "deposit_calc_method",
                    models.CharField(
                        choices=[
                            ("FLAT_FEE", "Flat Fee"),
                            ("PERCENTAGE", "Percentage of Booking Total"),
                        ],
                        default="FLAT_FEE",
                        help_text="Method to calculate the deposit amount.",
                        max_length=20,
                    ),
                ),
                (
                    "deposit_flat_fee_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Flat fee amount for deposit if 'Flat Fee' method is chosen.",
                        max_digits=10,
                    ),
                ),
                (
                    "deposit_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Percentage for deposit if 'Percentage' method is chosen (e.g., 0.1 for 10%).",
                        max_digits=5,
                    ),
                ),
                (
                    "enable_online_full_payment",
                    models.BooleanField(
                        default=False,
                        help_text="Allow customers to pay the full amount online.",
                    ),
                ),
                (
                    "enable_online_deposit",
                    models.BooleanField(
                        default=True,
                        help_text="Allow customers to pay the deposit amount online (if deposits are enabled).",
                    ),
                ),
                (
                    "enable_instore_full_payment",
                    models.BooleanField(
                        default=True,
                        help_text="Allow customers to opt for paying the full amount in-store.",
                    ),
                ),
                (
                    "currency_code",
                    models.CharField(
                        default="AUD",
                        help_text="Currency code (e.g., AUD, USD).",
                        max_length=3,
                    ),
                ),
                (
                    "currency_symbol",
                    models.CharField(
                        default="$",
                        help_text="Currency symbol (e.g., $).",
                        max_length=5,
                    ),
                ),
            ],
            options={
                "verbose_name": "Service Settings",
                "verbose_name_plural": "Service Settings",
            },
        ),
        migrations.CreateModel(
            name="ServiceType",
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
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField()),
                (
                    "estimated_duration",
                    models.IntegerField(
                        help_text="Estimated number of days to complete this service"
                    ),
                ),
                (
                    "base_price",
                    models.DecimalField(decimal_places=2, default=0.0, max_digits=8),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this service is currently offered",
                    ),
                ),
                (
                    "image",
                    models.FileField(
                        blank=True,
                        help_text="Icon image for this service type",
                        null=True,
                        upload_to="service_types/",
                    ),
                ),
            ],
            options={
                "verbose_name": "Service Type",
                "verbose_name_plural": "Service Types",
            },
        ),
        migrations.CreateModel(
            name="TempServiceBooking",
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
                    "session_uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for retrieving the temporary booking.",
                        unique=True,
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
                        help_text="The selected payment option for this booking.",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "service_date",
                    models.DateField(help_text="Requested date for the service."),
                ),
                (
                    "dropoff_date",
                    models.DateField(
                        blank=True,
                        help_text="Requested date for the drop off.",
                        null=True,
                    ),
                ),
                (
                    "dropoff_time",
                    models.TimeField(
                        blank=True,
                        help_text="Requested drop-off time for the service.",
                        null=True,
                    ),
                ),
                (
                    "estimated_pickup_date",
                    models.DateField(
                        blank=True,
                        help_text="Estimated pickup date set by admin.",
                        null=True,
                    ),
                ),
                (
                    "customer_notes",
                    models.TextField(
                        blank=True,
                        help_text="Any additional notes from the customer.",
                        null=True,
                    ),
                ),
                (
                    "calculated_deposit_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Calculated deposit amount, if applicable.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "calculated_total",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=0.0,
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Temporary Service Booking",
                "verbose_name_plural": "Temporary Service Bookings",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ServiceBooking",
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
                    "service_booking_reference",
                    models.CharField(blank=True, max_length=20, null=True, unique=True),
                ),
                (
                    "calculated_total",
                    models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
                ),
                (
                    "calculated_deposit_amount",
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
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        help_text="The ID of the Stripe Payment Intent associated with this booking.",
                        max_length=100,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "service_date",
                    models.DateField(help_text="Requested date for the service."),
                ),
                (
                    "dropoff_date",
                    models.DateField(help_text="Requested date for the drop off."),
                ),
                (
                    "dropoff_time",
                    models.TimeField(
                        help_text="Requested drop-off time for the service."
                    ),
                ),
                (
                    "estimated_pickup_date",
                    models.DateField(
                        blank=True,
                        help_text="Estimated pickup date set by admin.",
                        null=True,
                    ),
                ),
                (
                    "booking_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                            ("declined", "Declined by Admin"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("no_show", "No Show"),
                            ("DECLINED_REFUNDED", "Declined and Refunded"),
                        ],
                        default="PENDING_CONFIRMATION",
                        max_length=30,
                    ),
                ),
                (
                    "customer_notes",
                    models.TextField(
                        blank=True,
                        help_text="Any additional notes from the customer.",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer_motorcycle",
                    models.ForeignKey(
                        blank=True,
                        help_text="Chosen motorcycle for this service (set in a later step).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="service_bookings",
                        to="service.customermotorcycle",
                    ),
                ),
                (
                    "payment",
                    models.OneToOneField(
                        blank=True,
                        help_text="Link to the associated payment record.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="related_service_booking_payment",
                        to="payments.payment",
                    ),
                ),
            ],
            options={
                "verbose_name": "Service Booking",
                "verbose_name_plural": "Service Bookings",
                "ordering": ["-created_at"],
            },
        ),
    ]
