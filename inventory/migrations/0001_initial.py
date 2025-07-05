import datetime
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BlockedSalesDate",
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
                    models.DateField(
                        help_text="The start date of the blocked period for sales appointments."
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        help_text="The end date of the blocked period (inclusive) for sales appointments."
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        help_text="Optional description for the blocked period (e.g., 'Public Holiday', 'Staff Training').",
                        max_length=255,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Blocked Sales Date",
                "verbose_name_plural": "Blocked Sales Dates",
                "ordering": ["start_date"],
            },
        ),
        migrations.CreateModel(
            name="InventorySettings",
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
                    "enable_depositless_enquiry",
                    models.BooleanField(
                        default=True,
                        help_text="Allow customers to submit an enquiry for a motorcycle without requiring a deposit.",
                    ),
                ),
                (
                    "enable_reservation_by_deposit",
                    models.BooleanField(
                        default=True,
                        help_text="Allow customers to reserve a motorcycle by paying a deposit.",
                    ),
                ),
                (
                    "enable_viewing_for_enquiry",
                    models.BooleanField(
                        default=True,
                        help_text="Allow customers to request a specific viewing/appointment date/time within the deposit-less enquiry flow.",
                    ),
                ),
                (
                    "deposit_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("100.00"),
                        help_text="The fixed amount required for a motorcycle reservation deposit.",
                        max_digits=10,
                    ),
                ),
                (
                    "deposit_lifespan_days",
                    models.IntegerField(
                        default=5,
                        help_text="Number of days a deposit holds a motorcycle reservation. After this period, the reservation may expire.",
                    ),
                ),
                (
                    "enable_sales_new_bikes",
                    models.BooleanField(
                        default=True,
                        help_text="Enable the sales process for 'New' motorcycles in the inventory.",
                    ),
                ),
                (
                    "enable_sales_used_bikes",
                    models.BooleanField(
                        default=True,
                        help_text="Enable the sales process for 'Used' and 'Demo' motorcycles in the inventory.",
                    ),
                ),
                (
                    "require_drivers_license",
                    models.BooleanField(
                        default=False,
                        help_text="Require customers to provide driver's license details.",
                    ),
                ),
                (
                    "require_address_info",
                    models.BooleanField(
                        default=False,
                        help_text="Require customers to provide address details.",
                    ),
                ),
                (
                    "sales_booking_open_days",
                    models.CharField(
                        default="Mon,Tue,Wed,Thu,Fri,Sat",
                        help_text="Comma-separated list of days when sales appointments (test drives, viewings) are open.",
                        max_length=255,
                    ),
                ),
                (
                    "sales_appointment_start_time",
                    models.TimeField(
                        default=datetime.time(9, 0),
                        help_text="The earliest time a sales appointment can be scheduled.",
                    ),
                ),
                (
                    "sales_appointment_end_time",
                    models.TimeField(
                        default=datetime.time(17, 0),
                        help_text="The latest time a sales appointment can be scheduled.",
                    ),
                ),
                (
                    "sales_appointment_spacing_mins",
                    models.IntegerField(
                        default=30,
                        help_text="The minimum interval in minutes between two sales appointments on the same day.",
                    ),
                ),
                (
                    "max_advance_booking_days",
                    models.IntegerField(
                        default=90,
                        help_text="Maximum number of days in advance a customer can book a sales appointment.",
                    ),
                ),
                (
                    "min_advance_booking_hours",
                    models.IntegerField(
                        default=24,
                        help_text="Minimum number of hours notice required for a sales appointment.",
                    ),
                ),
                (
                    "currency_code",
                    models.CharField(
                        default="AUD",
                        help_text="The three-letter ISO currency code for sales transactions (e.g., AUD, USD).",
                        max_length=3,
                    ),
                ),
                (
                    "currency_symbol",
                    models.CharField(
                        default="$",
                        help_text="The currency symbol for sales transactions (e.g., $).",
                        max_length=5,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Inventory Settings",
                "verbose_name_plural": "Inventory Settings",
            },
        ),
        migrations.CreateModel(
            name="MotorcycleCondition",
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
                ("name", models.CharField(max_length=20, unique=True)),
                ("display_name", models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name="SalesProfile",
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
                    models.CharField(
                        blank=True,
                        help_text="Address line 1 (e.g., street number and name).",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "address_line_2",
                    models.CharField(
                        blank=True,
                        help_text="Address line 2 (e.g., apartment, suite, unit).",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        blank=True,
                        help_text="City of the customer's address.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        blank=True,
                        help_text="State, province, or region of the customer's address.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "post_code",
                    models.CharField(
                        blank=True,
                        help_text="Postal code or ZIP code of the customer's address.",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "country",
                    models.CharField(
                        blank=True,
                        help_text="Country of the customer's address.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "drivers_license_image",
                    models.FileField(
                        blank=True,
                        help_text="Image of the customer's driver's license.",
                        null=True,
                        upload_to="drivers_licenses/",
                    ),
                ),
                (
                    "drivers_license_number",
                    models.CharField(
                        blank=True,
                        help_text="Customer's driver's license number.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "drivers_license_expiry",
                    models.DateField(
                        blank=True,
                        help_text="Expiration date of the customer's driver's license.",
                        null=True,
                    ),
                ),
                (
                    "date_of_birth",
                    models.DateField(
                        blank=True, help_text="Customer's date of birth.", null=True
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="The date and time when this sales profile was created.",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="The date and time when this sales profile was last updated.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sales Profile",
                "verbose_name_plural": "Sales Profiles",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="TempSalesBooking",
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
                    "amount_paid",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="The amount paid for this booking (e.g., deposit amount). Defaults to 0.",
                        max_digits=10,
                    ),
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
                        help_text="Current payment status of the temporary booking (e.g., unpaid, deposit_paid).",
                        max_length=20,
                    ),
                ),
                (
                    "booking_status",
                    models.CharField(
                        choices=[
                            ("pending_confirmation", "Pending Confirmation"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                            ("declined", "Declined by Admin"),
                            ("completed", "Completed"),
                            ("no_show", "No Show"),
                            ("declined_refunded", "Declined and Refunded"),
                            ("reserved", "Reserved"),
                            ("enquired", "Enquired"),
                            ("pending_details", "Pending Details"),
                        ],
                        default="pending_details",
                        help_text="Current booking status (e.g., pending_confirmation, confirmed).",
                        max_length=30,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="AUD",
                        help_text="The three-letter ISO currency code for the booking (e.g., AUD).",
                        max_length=3,
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        help_text="The ID of the Stripe Payment Intent associated with this booking, if applicable.",
                        max_length=100,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "request_viewing",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if the customer specifically requested a viewing/test drive in a deposit-less enquiry flow.",
                    ),
                ),
                (
                    "appointment_date",
                    models.DateField(
                        blank=True,
                        help_text="Requested date for the test drive or appointment.",
                        null=True,
                    ),
                ),
                (
                    "appointment_time",
                    models.TimeField(
                        blank=True,
                        help_text="Requested time for the test drive or appointment.",
                        null=True,
                    ),
                ),
                (
                    "customer_notes",
                    models.TextField(
                        blank=True,
                        help_text="Any additional notes or messages provided by the customer during the process.",
                        null=True,
                    ),
                ),
                (
                    "terms_accepted",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if the customer accepted the terms and conditions.",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="The date and time when this temporary booking was created.",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="The date and time when this temporary booking was last updated.",
                    ),
                ),
                (
                    "deposit_required_for_flow",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this temporary booking initiated a flow requiring a deposit.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Temporary Sales Booking",
                "verbose_name_plural": "Temporary Sales Bookings",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Motorcycle",
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
                ("title", models.CharField(max_length=200)),
                ("brand", models.CharField(max_length=100)),
                ("model", models.CharField(max_length=100)),
                ("year", models.IntegerField()),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Sale price (if applicable)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "vin_number",
                    models.CharField(
                        blank=True,
                        help_text="Vehicle Identification Number",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "engine_number",
                    models.CharField(
                        blank=True,
                        help_text="Engine number/identifier",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "condition",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("new", "New"),
                            ("used", "Used"),
                            ("demo", "Demo"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("for_sale", "For Sale"),
                            ("sold", "Sold"),
                            ("reserved", "Reserved"),
                            ("unavailable", "Unavailable"),
                            ("reserved", "Reserved"),
                        ],
                        default="for_sale",
                        help_text="The sales status of the motorcycle.",
                        max_length=20,
                    ),
                ),
                ("odometer", models.IntegerField(default=0)),
                (
                    "engine_size",
                    models.IntegerField(
                        help_text="Engine size in cubic centimeters (cc)"
                    ),
                ),
                (
                    "seats",
                    models.IntegerField(
                        blank=True,
                        help_text="Number of seats on the motorcycle",
                        null=True,
                    ),
                ),
                (
                    "transmission",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("automatic", "Automatic"),
                            ("manual", "Manual"),
                            ("semi-auto", "Semi-Automatic"),
                        ],
                        help_text="Motorcycle transmission type",
                        max_length=20,
                        null=True,
                    ),
                ),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "image",
                    models.FileField(blank=True, null=True, upload_to="motorcycles/"),
                ),
                ("date_posted", models.DateTimeField(auto_now_add=True)),
                (
                    "rego",
                    models.CharField(
                        blank=True,
                        help_text="Registration number",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "rego_exp",
                    models.DateField(
                        blank=True, help_text="Registration expiration date", null=True
                    ),
                ),
                (
                    "stock_number",
                    models.CharField(blank=True, max_length=50, null=True, unique=True),
                ),
                (
                    "conditions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Select all applicable conditions (e.g., Used)",
                        related_name="motorcycles",
                        to="inventory.motorcyclecondition",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MotorcycleImage",
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
                ("image", models.FileField(upload_to="motorcycles/additional/")),
                (
                    "motorcycle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="inventory.motorcycle",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SalesBooking",
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
                    "sales_booking_reference",
                    models.CharField(
                        blank=True,
                        help_text="A unique reference code for the sales booking.",
                        max_length=20,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "amount_paid",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="The total amount paid for this booking (e.g., deposit or full payment).",
                        max_digits=10,
                    ),
                ),
                (
                    "payment_status",
                    models.CharField(
                        choices=[
                            ("unpaid", "Unpaid"),
                            ("deposit_paid", "Deposit Paid"),
                            ("refunded", "Refunded"),
                        ],
                        default="unpaid",
                        help_text="Current payment status of the booking (e.g., unpaid, deposit_paid, paid).",
                        max_length=20,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="AUD",
                        help_text="The three-letter ISO currency code for the booking (e.g., AUD).",
                        max_length=3,
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        help_text="The ID of the Stripe Payment Intent associated with this booking, if applicable.",
                        max_length=100,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "request_viewing",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if the customer specifically requested a viewing/test drive in a deposit-less enquiry flow.",
                    ),
                ),
                (
                    "appointment_date",
                    models.DateField(
                        blank=True,
                        help_text="Confirmed date for the test drive, appointment, or pickup.",
                        null=True,
                    ),
                ),
                (
                    "appointment_time",
                    models.TimeField(
                        blank=True,
                        help_text="Confirmed time for the test drive, appointment, or pickup.",
                        null=True,
                    ),
                ),
                (
                    "booking_status",
                    models.CharField(
                        choices=[
                            ("pending_confirmation", "Pending Confirmation"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                            ("declined", "Declined by Admin"),
                            ("completed", "Completed"),
                            ("no_show", "No Show"),
                            ("declined_refunded", "Declined and Refunded"),
                            ("enquired", "Enquired"),
                        ],
                        default="pending_confirmation",
                        help_text="The current status of the sales booking (e.g., confirmed, reserved, enquired, completed).",
                        max_length=30,
                    ),
                ),
                (
                    "customer_notes",
                    models.TextField(
                        blank=True,
                        help_text="Any additional notes or messages provided by the customer.",
                        null=True,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="The date and time when this sales booking was created.",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="The date and time when this sales booking was last updated.",
                    ),
                ),
                (
                    "motorcycle",
                    models.ForeignKey(
                        help_text="The motorcycle associated with this sales booking.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sales_bookings",
                        to="inventory.motorcycle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sales Booking",
                "verbose_name_plural": "Sales Bookings",
                "ordering": ["-created_at"],
            },
        ),
    ]
