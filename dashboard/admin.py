from django.contrib import admin                                     
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
                                                        
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
                'enable_sales_new', 'enable_sales_used', 'enable_service_booking',
                'enable_user_accounts', 'enable_contact_page', 'enable_about_page',
                'enable_map_display', 'enable_featured_section', 'display_new_prices',
                'display_used_prices', 'enable_privacy_policy_page', 'enable_returns_page',
                'enable_security_page', 'enable_terms_page', 'enable_google_places_reviews',
            )
        }),
        ('Service Settings', {
            'fields': (
                'allow_anonymous_bookings', 'allow_account_bookings', 'booking_open_days',
                'drop_off_start_time', 'drop_off_end_time', 'booking_advance_notice',
                'max_visible_slots_per_day', 'service_confirmation_email_subject',
                'service_pending_email_subject', 'admin_service_notification_email',
            )
        }),
        ('Miscellaneous Settings', {
             'fields': (                                                                                                                 
             )
        }),
    )
                                                
    def has_add_permission(self, request):
        return SiteSettings.objects.count() == 0

                                                          
    def has_delete_permission(self, request, obj=None):
        return False