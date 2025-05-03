# dashboard/admin.py

from django.contrib import admin

# Import models from the dashboard app
from .models import AboutPageContent, SiteSettings

# Register your models here.

@admin.register(AboutPageContent)
class AboutPageContentAdmin(admin.ModelAdmin):
    # Copy the fieldsets or fields from your old AboutPageContentAdmin
    # Use fieldsets for better organization in the admin change form
    fieldsets = (
        ('Introduction', {
            'fields': ('intro_text',)
        }),
        ('Sales Section', {
            'fields': ('sales_title', 'sales_content', 'sales_image')
        }),
        ('Service Section', {
            'fields': ('service_title', 'service_content', 'service_image')
        }),
        ('Parts & Accessories Section', {
            'fields': ('parts_title', 'parts_content', 'parts_image')
        }),
        ('Call to Action', {
            'fields': ('cta_text',)
        }),
    )
    # If you only want one instance, prevent adding more
    def has_add_permission(self, request):
        # Check if there's already an instance (assuming you only want one AboutPageContent)
        return AboutPageContent.objects.count() == 0

    # If you only want one instance, prevent deleting the existing one
    def has_delete_permission(self, request, obj=None):
        # Allow deletion only if there's more than one instance, or prevent entirely
        return AboutPageContent.objects.count() > 1 # Or return False to prevent all deletion


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    # Use fieldsets to organize the many settings fields
    fieldsets = (
        ('Business Information', {
            'fields': ('phone_number', 'email_address', 'storefront_address', 'google_places_place_id')
        }),
        ('Business Hours', {
            'fields': (
                'opening_hours_monday', 'opening_hours_tuesday', 'opening_hours_wednesday',
                'opening_hours_thursday', 'opening_hours_friday', 'opening_hours_saturday',
                'opening_hours_sunday',
            )
        }),
        ('Visibility Settings', {
            'fields': (
                'enable_sales_new', 'enable_sales_used', 'enable_hire', 'enable_service_booking',
                'enable_user_accounts', 'enable_contact_page', 'enable_about_page',
                'enable_map_display', 'enable_featured_section', 'display_new_prices',
                'display_used_prices', 'enable_privacy_policy_page', 'enable_returns_page',
                'enable_security_page', 'enable_terms_page', 'enable_google_places_reviews',
            )
        }),
        ('Service Booking Settings', {
            'fields': (
                'allow_anonymous_bookings', 'allow_account_bookings', 'booking_open_days',
                'booking_start_time', 'booking_end_time', 'booking_advance_notice',
                'max_visible_slots_per_day', 'service_confirmation_email_subject',
                'service_pending_email_subject', 'admin_service_notification_email',
            )
        }),
        ('Hire Booking Settings', {
            'fields': (
                'minimum_hire_duration_days', 'maximum_hire_duration_days', 'hire_booking_advance_notice',
                'default_hire_deposit_percentage', 'hire_confirmation_email_subject', 'admin_hire_notification_email',
            )
        }),
        ('Miscellaneous Settings', {
             'fields': (
                 # Add any other miscellaneous fields from SiteSettings model here
                 #'enable_random_featured_ordering', # Example field
             )
        }),
    )
    # Assuming only one instance of SiteSettings
    def has_add_permission(self, request):
        return SiteSettings.objects.count() == 0

    # Prevent deleting the single instance of SiteSettings
    def has_delete_permission(self, request, obj=None):
        return False