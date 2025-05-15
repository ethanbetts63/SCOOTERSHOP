from django.db import models
from datetime import time
from django.core.exceptions import ImproperlyConfigured

# Model for storing site-wide settings and configuration options
class SiteSettings(models.Model):
    """
    Model for storing site-wide settings and configuration options
    """
    # Visibility Fields - control which features are enabled on the site
    enable_sales_new = models.BooleanField(default=True, help_text="Enable new motorcycle sales")
    enable_sales_used = models.BooleanField(default=True, help_text="Enable used motorcycle sales")
    enable_hire = models.BooleanField(default=True, help_text="Enable motorcycle hire services")
    enable_service_booking = models.BooleanField(default=True, help_text="Enable service booking functionality")
    enable_user_accounts = models.BooleanField(default=True, help_text="Enable user account registration")
    enable_contact_page = models.BooleanField(default=True, help_text="Enable the contact us page")
    enable_about_page = models.BooleanField(default=True, help_text="Enable the about us page")
    enable_map_display = models.BooleanField(default=True, help_text="Enable displaying a map (e.g., location map)")
    enable_featured_section = models.BooleanField(default=True, help_text="Enable a featured items or content section")
    enable_privacy_policy_page = models.BooleanField(default=True, help_text="Enable the privacy policy page")
    enable_returns_page = models.BooleanField(default=True, help_text="Enable the returns page")
    enable_security_page = models.BooleanField(default=True, help_text="Enable the security page")
    enable_terms_page = models.BooleanField(default=True, help_text="Enable the terms and conditions page")
    enable_google_places_reviews = models.BooleanField(default=True, help_text="Enable displaying Google Places reviews")

    # Service Booking Fields (Settings related to service booking)
    allow_anonymous_bookings = models.BooleanField(default=True, help_text="Allow service bookings without an account")
    allow_account_bookings = models.BooleanField(default=True, help_text="Allow service bookings with an account")
    booking_open_days = models.IntegerField(default=60, help_text="Number of days in advance that bookings can be made")
    drop_off_start_time = models.TimeField(default=time(9, 0), help_text="Earliest time of day for service drop-offs (e.g., 09:00)")
    drop_off_end_time = models.TimeField(default=time(17, 0), help_text="Latest time of day for service drop-offs (e.g., 17:00)")
    booking_advance_notice = models.IntegerField(default=1, help_text="Minimum number of days notice required for a booking")
    max_visible_slots_per_day = models.IntegerField(default=6, help_text="Maximum number of booking slots to show per day")
    service_confirmation_email_subject = models.CharField(max_length=200, default="Your service booking has been confirmed")
    service_pending_email_subject = models.CharField(max_length=200, default="Your service booking request has been received")
    admin_service_notification_email = models.EmailField(blank=True, null=True, help_text="Email address for service booking notifications")

    # Sales Fields (Settings related to sales display)
    display_new_prices = models.BooleanField(default=True, help_text="Display prices for new motorcycles")
    display_used_prices = models.BooleanField(default=True, help_text="Display prices for used motorcycles")

    # Business Fields (General business contact info)
    phone_number = models.CharField(max_length=20, blank=True, null=True, default='(08) 9433 4613')
    email_address = models.EmailField(blank=True, null=True, default='admin@scootershop.com.au')
    storefront_address = models.TextField(blank=True, null=True, default='Unit 2/95 Queen Victoria St, Fremantle WA, Australia')
    google_places_place_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Places Place ID for the storefront location", default="ChIJy_zrHmGhMioRisz6mis0SpQ")

    # Business Hours
    opening_hours_monday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_tuesday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_wednesday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_thursday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_friday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 5:00pm')
    opening_hours_saturday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='10:30am to 1:00pm (By Appointment only)')
    opening_hours_sunday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='Closed')

    # System fields
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Site Settings"

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        """
        Ensure there is only ever one instance of SiteSettings
        """
        # If this is the first save and an instance already exists, don't save
        if not self.pk and SiteSettings.objects.exists():
             # Decide how to handle this - maybe raise an error or just return
             # Raising an error is safer to prevent accidental duplicates
             raise ImproperlyConfigured("Only one SiteSettings instance is allowed.")
        return super(SiteSettings, self).save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """
        Returns the settings instance, creating it if necessary.
        Use a try-except to handle the potential ImproperlyConfigured from save.
        """
        try:
            # Try to get the existing instance
            settings = cls.objects.get(pk=1)
        except cls.DoesNotExist:
            # If it doesn't exist, create it
            try:
                settings = cls.objects.create(pk=1)
            except ImproperlyConfigured:
                # If creating fails (shouldn't happen if pk=1 is unique and no instance existed)
                # This is a fallback, the primary check is in the save method
                settings = cls.objects.get(pk=1) # Attempt to get it again
        return settings

    @classmethod
    def get_service_booking_settings(cls):
        """
        Returns the service booking related settings
        """
        settings = cls.get_settings()
        return {
            'allow_anonymous_bookings': settings.allow_anonymous_bookings,
            'allow_account_bookings': settings.allow_account_bookings,
            'booking_open_days': settings.booking_open_days,
            'drop_off_start_time': settings.drop_off_start_time,
            'drop_off_end_time': settings.drop_off_end_time,
            'booking_advance_notice': settings.booking_advance_notice,
            'max_visible_slots_per_day': settings.max_visible_slots_per_day,
        }

    @classmethod
    def get_business_hours(cls):
        """
        Returns the business hours settings as a dictionary
        """
        settings = cls.get_settings()
        return {
            'monday': settings.opening_hours_monday,
            'tuesday': settings.opening_hours_tuesday,
            'wednesday': settings.opening_hours_wednesday,
            'thursday': settings.opening_hours_thursday,
            'friday': settings.opening_hours_friday,
            'saturday': settings.opening_hours_saturday,
            'sunday': settings.opening_hours_sunday,
        }