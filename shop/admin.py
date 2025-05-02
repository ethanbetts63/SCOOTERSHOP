# SCOOTER_SHOP/shop/admin.py

from django.contrib import admin
# Import your models from the new shop/models.py
from .models import AboutPageContent, CustomerMotorcycle, ServiceBooking, ServiceType, SiteSettings, Motorcycle, MotorcycleCondition, MotorcycleImage, User # Add all models you want to register

# Register your models here.

@admin.register(AboutPageContent)
class AboutPageContentAdmin(admin.ModelAdmin):
    # Copy the fieldsets or fields from your old AboutPageContentAdmin
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

    def has_add_permission(self, request):
        # Check if there's already an instance (assuming you only want one AboutPageContent)
        return AboutPageContent.objects.count() == 0

# Example: Register other models you want in the Admin
# @admin.register(CustomerMotorcycle)
# class CustomerMotorcycleAdmin(admin.ModelAdmin):
#     list_display = ('year', 'make', 'model', 'owner')
#     search_fields = ('make', 'model', 'owner__username')

# @admin.register(ServiceBooking)
# class ServiceBookingAdmin(admin.ModelAdmin):
#     list_display = ('booking_reference', 'service_type', 'status', 'preferred_date', 'customer_name', 'customer_email')
#     list_filter = ('status', 'service_type', 'preferred_date')
#     search_fields = ('booking_reference', 'customer_name', 'customer_email', 'customer_phone', 'motorcycle__make', 'motorcycle__model')
#     raw_id_fields = ('motorcycle', 'customer_user') # Use raw_id_fields for ForeignKey to User/Motorcycle if you have many instances

# @admin.register(ServiceType)
# class ServiceTypeAdmin(admin.ModelAdmin):
#     list_display = ('name', 'price', 'estimated_duration')

# @admin.register(SiteSettings)
# class SiteSettingsAdmin(admin.ModelAdmin):
#     # Assuming only one instance of SiteSettings
#     def has_add_permission(self, request):
#         return SiteSettings.objects.count() == 0

# Add registrations for any other models you want in the Admin
# admin.site.register(Motorcycle)
# admin.site.register(MotorcycleCondition)
# admin.site.register(MotorcycleImage)
# If you are using a custom User model from shop.models, you might need to
# unregister the default User admin and register your custom one if needed.
# from django.contrib.auth.admin import UserAdmin
# admin.site.unregister(User)
# @admin.register(User)
# class CustomUserAdmin(UserAdmin):
#     pass # Or customize as needed
