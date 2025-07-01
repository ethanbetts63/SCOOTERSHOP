                  

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
    list_display = ('year', 'brand', 'model', 'service_profile_name', 'rego')
    list_filter = ('brand', 'year')
    search_fields = ('brand', 'model', 'rego', 'vin_number', 'service_profile__name', 'service_profile__email')
    raw_id_fields = ('service_profile',)                                                        

    def service_profile_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"
    service_profile_name.short_description = 'Owner Name'

@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        'service_booking_reference',
        'service_type',
        'booking_status',                       
        'dropoff_date',                         
        'dropoff_time',                         
        'customer_name',
        'customer_email',
        'motorcycle_info',
        'payment_status',                       
    )
    list_filter = ('booking_status', 'service_type', 'dropoff_date', 'payment_status')                        
    search_fields = (
        'booking_reference',
        'service_profile__name',
        'service_profile__email',
        'service_profile__phone_number',
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
            return f"{obj.customer_motorcycle.year} {obj.customer_motorcycle.brand}"
        return "N/A"
    motorcycle_info.short_description = 'Motorcycle'

@admin.register(ServiceProfile)
class ServiceProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'city', 'country', 'user_link')
    list_filter = ('country', 'city')
    search_fields = ('name', 'email', 'phone_number', 'user__username', 'city', 'post_code')
    raw_id_fields = ('user',)                                             

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
                                                                         
                                                                          
    list_filter = ('enable_service_booking', 'allow_anonymous_bookings', 'enable_deposit')

                                                                     
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
        'payment_method',
        'created_at',
    )
    list_filter = ('service_type', 'dropoff_date', 'payment_method')
    search_fields = (
        'session_uuid',
        'service_profile__name',
        'service_profile__email',
        'customer_motorcycle__model',
    )
    raw_id_fields = ('service_type', 'service_profile', 'customer_motorcycle')

    def service_profile_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"
    service_profile_name.short_description = 'Customer Name (Temp)'
