# service/admin.py

from django.contrib import admin
from service.models import (
    ServiceType,
    CustomerMotorcycle,
    ServiceBooking,
    ServiceProfile,
    ServiceBrand,
    ServiceSettings,
    BlockedServiceDate,
    TempServiceBooking,
)

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'estimated_duration', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(CustomerMotorcycle)
class CustomerMotorcycleAdmin(admin.ModelAdmin):
    list_display = ('year', 'brand', 'make', 'model', 'service_profile_name', 'rego')
    list_filter = ('brand', 'make', 'year')
    search_fields = ('brand', 'make', 'model', 'rego', 'vin_number', 'service_profile__name', 'service_profile__email')
    raw_id_fields = ('service_profile',) # Use if you have many service profiles for performance

    def service_profile_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"
    service_profile_name.short_description = 'Owner Name'

@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_reference',
        'service_type',
        'booking_status', # Corrected field name
        'dropoff_date',   # Corrected field name
        'dropoff_time',   # Corrected field name
        'customer_name',
        'customer_email',
        'motorcycle_info',
        'payment_status', # Added payment status
    )
    list_filter = ('booking_status', 'service_type', 'dropoff_date', 'payment_status') # Corrected field names
    search_fields = (
        'booking_reference',
        'service_profile__name',
        'service_profile__email',
        'service_profile__phone_number',
        'customer_motorcycle__make',
        'customer_motorcycle__model',
    )
    raw_id_fields = ('service_type', 'service_profile', 'customer_motorcycle', 'payment')

    def customer_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"
    customer_name.short_description = 'Customer Name'

    def customer_email(self, obj):
        return obj.service_profile.email if obj.service_profile else "N/A"
    customer_email.short_description = 'Customer Email'

    def motorcycle_info(self, obj):
        if obj.customer_motorcycle:
            return f"{obj.customer_motorcycle.year} {obj.customer_motorcycle.brand} {obj.customer_motorcycle.make}"
        return "N/A"
    motorcycle_info.short_description = 'Motorcycle'

@admin.register(ServiceProfile)
class ServiceProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'city', 'country', 'user_link')
    list_filter = ('country', 'city')
    search_fields = ('name', 'email', 'phone_number', 'user__username', 'city', 'post_code')
    raw_id_fields = ('user',) # Use if you have many users for performance

    def user_link(self, obj):
        if obj.user:
            return f"{obj.user.username} (ID: {obj.user.id})"
        return "Anonymous"
    user_link.short_description = 'Associated User'

@admin.register(ServiceBrand)
class ServiceBrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_updated')
    search_fields = ('name',)

@admin.register(ServiceSettings)
class ServiceSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'enable_service_booking',
        'allow_anonymous_bookings',
        'enable_deposit',
        'currency_code',
    )
    # Since there's only one instance, list_filter might not be as useful
    # but you can add it if you have boolean fields you want to filter by.
    list_filter = ('enable_service_booking', 'allow_anonymous_bookings', 'enable_deposit')

    # Prevent adding new instances from the admin (singleton pattern)
    def has_add_permission(self, request):
        return not ServiceSettings.objects.exists()

@admin.register(BlockedServiceDate)
class BlockedServiceDateAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'description')
    list_filter = ('start_date', 'end_date')
    search_fields = ('description',)

@admin.register(TempServiceBooking)
class TempServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        'session_uuid',
        'service_type',
        'service_profile_name',
        'dropoff_date',
        'dropoff_time',
        'payment_option',
        'created_at',
    )
    list_filter = ('service_type', 'dropoff_date', 'payment_option')
    search_fields = (
        'session_uuid',
        'service_profile__name',
        'service_profile__email',
        'customer_motorcycle__make',
        'customer_motorcycle__model',
    )
    raw_id_fields = ('service_type', 'service_profile', 'customer_motorcycle')

    def service_profile_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"
    service_profile_name.short_description = 'Customer Name (Temp)'
