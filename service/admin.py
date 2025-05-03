# service/admin.py

from django.contrib import admin

# Import models from the service app
from .models import ServiceType, CustomerMotorcycle, ServiceBooking

# Register your models here.

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'estimated_duration', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(CustomerMotorcycle)
class CustomerMotorcycleAdmin(admin.ModelAdmin):
    list_display = ('year', 'make', 'model', 'owner', 'rego')
    list_filter = ('make', 'year')
    search_fields = ('make', 'model', 'rego', 'vin_number', 'owner__username', 'owner__email')
    # raw_id_fields = ('owner',) # Use if you have many users for performance

@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'service_type', 'status', 'appointment_datetime', 'customer_name', 'customer_email', 'motorcycle_info')
    list_filter = ('status', 'service_type', 'appointment_datetime')
    search_fields = ('booking_reference', 'customer_name', 'customer_email', 'customer_phone', 'motorcycle__make', 'motorcycle__model')
    # raw_id_fields = ('motorcycle', 'customer_user') # Use for ForeignKey/OneToOne fields if many instances

    # Custom method to display motorcycle info in list_display
    def motorcycle_info(self, obj):
        if obj.motorcycle:
            return f"{obj.motorcycle.year} {obj.motorcycle.make} {obj.motorcycle.model}"
        return "N/A"
    motorcycle_info.short_description = 'Motorcycle'