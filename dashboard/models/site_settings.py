from django.db import models
from django.core.exceptions import ImproperlyConfigured


class SiteSettings(models.Model):
    enable_sales_new = models.BooleanField(
        default=True, help_text="Enable new motorcycle sales"
    )
    enable_sales_used = models.BooleanField(
        default=True, help_text="Enable used motorcycle sales"
    )
    enable_service_booking = models.BooleanField(
        default=True, help_text="Enable service booking functionality"
    )
    enable_contact_page = models.BooleanField(
        default=True, help_text="Enable the contact us page"
    )
    enable_map_display = models.BooleanField(
        default=True, help_text="Enable displaying a map (e.g., location map)"
    )
    enable_privacy_policy_page = models.BooleanField(
        default=True, help_text="Enable the privacy policy page"
    )
    enable_returns_page = models.BooleanField(
        default=True, help_text="Enable the returns page"
    )
    enable_security_page = models.BooleanField(
        default=True, help_text="Enable the security page"
    )
    enable_google_places_reviews = models.BooleanField(
        default=True, help_text="Enable displaying Google Places reviews"
    )
    enable_user_accounts = models.BooleanField(
        default=True, help_text="Enable user account registration"
    )

    display_phone_number = models.BooleanField(
        default=False, help_text="Display the phone number on the website."
    )
    display_address = models.BooleanField(
        default=True, help_text="Display the storefront address on the website."
    )
    display_opening_hours = models.BooleanField(
        default=True, help_text="Display the opening hours on the website."
    )
    enable_faq_service = models.BooleanField(
        default=True, help_text="Enable the faq section for services."
    )
    enable_faq_sales = models.BooleanField(
        default=True, help_text="Enable the faq section for sales."
    )
    enable_refunds = models.BooleanField(
        default=False, help_text="Enable the refunds page."
    )
    enable_motorcycle_mover = models.BooleanField(
        default=True, help_text="Enable the motorcycle mover section."
    )

    phone_number = models.CharField(
        max_length=20, blank=True, null=True, default="(08) 9433 4613"
    )
    email_address = models.EmailField(
        blank=True, null=True, default="admin@scootershop.com.au"
    )

    street_address = models.CharField(
        max_length=255, blank=True, null=True, default="Unit 2/95 Queen Victoria St"
    )
    address_locality = models.CharField(
        max_length=100, blank=True, null=True, default="Fremantle"
    )
    address_region = models.CharField(
        max_length=100, blank=True, null=True, default="WA"
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True, default="6160")

    google_places_place_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Google Places Place ID for the storefront location",
        default="ChIJy_zrHmGhMioRisz6mis0SpQ",
    )
    google_business_page_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional URL to the Google Business page.",
    )
    youtube_link = models.CharField(max_length=255, blank=True, null=True)
    instagram_link = models.CharField(max_length=255, blank=True, null=True)
    facebook_link = models.CharField(max_length=255, blank=True, null=True)

    opening_hours_monday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )
    opening_hours_tuesday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )
    opening_hours_wednesday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )
    opening_hours_thursday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )
    opening_hours_friday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )
    opening_hours_saturday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )
    opening_hours_sunday = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'",
        default="By Appointment Only",
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Site Settings"

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ImproperlyConfigured("Only one SiteSettings instance is allowed.")
        return super(SiteSettings, self).save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        try:
            settings = cls.objects.get(pk=1)
        except cls.DoesNotExist:
            try:
                settings = cls.objects.create(pk=1)
            except ImproperlyConfigured:
                settings = cls.objects.get(pk=1)
        return settings
