                                             

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AboutPageContent",
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
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "intro_text",
                    models.TextField(
                        help_text="Introduction text at the top of the About page"
                    ),
                ),
                ("sales_title", models.CharField(default="Sales", max_length=100)),
                (
                    "sales_content",
                    models.TextField(help_text="Content for the Sales section"),
                ),
                (
                    "sales_image",
                    models.FileField(
                        blank=True,
                        help_text="Image for the Sales section",
                        null=True,
                        upload_to="about/",
                    ),
                ),
                ("service_title", models.CharField(default="Service", max_length=100)),
                (
                    "service_content",
                    models.TextField(help_text="Content for the Service section"),
                ),
                (
                    "service_image",
                    models.FileField(
                        blank=True,
                        help_text="Image for the Service section",
                        null=True,
                        upload_to="about/",
                    ),
                ),
                (
                    "parts_title",
                    models.CharField(default="Parts & Accessories", max_length=100),
                ),
                (
                    "parts_content",
                    models.TextField(
                        help_text="Content for the Parts & Accessories section"
                    ),
                ),
                (
                    "parts_image",
                    models.FileField(
                        blank=True,
                        help_text="Image for the Parts section",
                        null=True,
                        upload_to="about/",
                    ),
                ),
                (
                    "cta_text",
                    models.TextField(
                        help_text="Call to action text at the bottom of the page"
                    ),
                ),
            ],
            options={
                "verbose_name": "About Page Content",
                "verbose_name_plural": "About Page Content",
            },
        ),
        
        
        migrations.CreateModel(
            name="SiteSettings",
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
                    "enable_sales_new",
                    models.BooleanField(
                        default=True, help_text="Enable new motorcycle sales"
                    ),
                ),
                (
                    "enable_sales_used",
                    models.BooleanField(
                        default=True, help_text="Enable used motorcycle sales"
                    ),
                ),
                
                (
                    "enable_service_booking",
                    models.BooleanField(
                        default=True, help_text="Enable service booking functionality"
                    ),
                ),
                (
                    "enable_user_accounts",
                    models.BooleanField(
                        default=True, help_text="Enable user account registration"
                    ),
                ),
                (
                    "enable_contact_page",
                    models.BooleanField(
                        default=True, help_text="Enable the contact us page"
                    ),
                ),
                (
                    "enable_map_display",
                    models.BooleanField(
                        default=True,
                        help_text="Enable displaying a map (e.g., location map)",
                    ),
                ),
                (
                    "enable_privacy_policy_page",
                    models.BooleanField(
                        default=True, help_text="Enable the privacy policy page"
                    ),
                ),
                (
                    "enable_returns_page",
                    models.BooleanField(
                        default=True, help_text="Enable the returns page"
                    ),
                ),
                (
                    "enable_security_page",
                    models.BooleanField(
                        default=True, help_text="Enable the security page"
                    ),
                ),
                (
                    "enable_google_places_reviews",
                    models.BooleanField(
                        default=True,
                        help_text="Enable displaying Google Places reviews",
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        blank=True, default="(08) 9433 4613", max_length=20, null=True
                    ),
                ),
                (
                    "email_address",
                    models.EmailField(
                        blank=True,
                        default="admin@scootershop.com.au",
                        max_length=254,
                        null=True,
                    ),
                ),
                (
                    "storefront_address",
                    models.TextField(
                        blank=True,
                        default="Unit 2/95 Queen Victoria St, Fremantle WA, Australia",
                        null=True,
                    ),
                ),
                (
                    "google_places_place_id",
                    models.CharField(
                        blank=True,
                        default="ChIJy_zrHmGhMioRisz6mis0SpQ",
                        help_text="Google Places Place ID for the storefront location",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_monday",
                    models.CharField(
                        blank=True,
                        default="10:30am to 5:00pm",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_tuesday",
                    models.CharField(
                        blank=True,
                        default="10:30am to 5:00pm",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_wednesday",
                    models.CharField(
                        blank=True,
                        default="10:30am to 5:00pm",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_thursday",
                    models.CharField(
                        blank=True,
                        default="10:30am to 5:00pm",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_friday",
                    models.CharField(
                        blank=True,
                        default="10:30am to 5:00pm",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_saturday",
                    models.CharField(
                        blank=True,
                        default="10:30am to 1:00pm (By Appointment only)",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "opening_hours_sunday",
                    models.CharField(
                        blank=True,
                        default="Closed",
                        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
                        max_length=100,
                        null=True,
                    ),
                ),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Site Settings",
                "verbose_name_plural": "Site Settings",
            },
        ),
    ]
