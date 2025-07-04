from django.db import models
from datetime import time
from django.core.exceptions import ImproperlyConfigured

                                                                
class SiteSettings(models.Model):
    """
    Model for storing site-wide settings and configuration options
    """
                                                                        
    enable_sales_new = models.BooleanField(default=True, help_text="Enable new motorcycle sales")
    enable_sales_used = models.BooleanField(default=True, help_text="Enable used motorcycle sales")
    enable_service_booking = models.BooleanField(default=True, help_text="Enable service booking functionality")
    enable_contact_page = models.BooleanField(default=True, help_text="Enable the contact us page")
    enable_map_display = models.BooleanField(default=True, help_text="Enable displaying a map (e.g., location map)")
    enable_privacy_policy_page = models.BooleanField(default=True, help_text="Enable the privacy policy page")
    enable_returns_page = models.BooleanField(default=True, help_text="Enable the returns page")
    enable_security_page = models.BooleanField(default=True, help_text="Enable the security page")
    enable_google_places_reviews = models.BooleanField(default=True, help_text="Enable displaying Google Places reviews")
    enable_user_accounts = models.BooleanField(default=True, help_text="Enable user account registration")

    # New visibility fields
    display_phone_number = models.BooleanField(default=False, help_text="Display the phone number on the website.")
    display_address = models.BooleanField(default=True, help_text="Display the storefront address on the website.")
    display_opening_hours = models.BooleanField(default=True, help_text="Display the opening hours on the website.")
    enable_faq_service = models.BooleanField(default=True, help_text="Enable the FAQ section for services.")
    enable_faq_sales = models.BooleanField(default=True, help_text="Enable the FAQ section for sales.")
                                                     
    phone_number = models.CharField(max_length=20, blank=True, null=True, default='(08) 9433 4613')
    email_address = models.EmailField(blank=True, null=True, default='admin@scootershop.com.au')
    storefront_address = models.TextField(blank=True, null=True, default='Unit 2/95 Queen Victoria St, Fremantle WA, Australia')
    google_places_place_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Places Place ID for the storefront location", default="ChIJy_zrHmGhMioRisz6mis0SpQ")
    youtube_link = models.CharField(max_length=255, blank=True, null=True)
    instagram_link = models.CharField(max_length=255, blank=True, null=True)
    facebook_link = models.CharField(max_length=255, blank=True, null=True) 
                    
    opening_hours_monday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')
    opening_hours_tuesday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')
    opening_hours_wednesday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')
    opening_hours_thursday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')
    opening_hours_friday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')
    opening_hours_saturday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')
    opening_hours_sunday = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '9:00 AM - 5:00 PM' or 'Closed'", default='By Appointment Only')

                   
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
                                                                              
        if not self.pk and SiteSettings.objects.exists():
                                                                              
                                                                         
             raise ImproperlyConfigured("Only one SiteSettings instance is allowed.")
        return super(SiteSettings, self).save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """
        Returns the settings instance, creating it if necessary.
        Use a try-except to handle the potential ImproperlyConfigured from save.
        """
        try:
                                              
            settings = cls.objects.get(pk=1)
        except cls.DoesNotExist:
                                            
            try:
                settings = cls.objects.create(pk=1)
            except ImproperlyConfigured:
                                                                                                
                                                                             
                settings = cls.objects.get(pk=1)                          
        return settings

    @classmethod
    def get_service_settings(cls):
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
