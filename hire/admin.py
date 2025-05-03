# hire/admin.py

from django.contrib import admin

# Import models from the hire app (assuming HireBooking is here)
# from .models import HireBooking

# Register your models here.

# @admin.register(HireBooking)
# class HireBookingAdmin(admin.ModelAdmin):
#     list_display = ('booking_reference', 'motorcycle', 'start_date', 'end_date', 'status', 'customer_name', 'customer_email')
#     list_filter = ('status', 'motorcycle', 'start_date', 'end_date')
#     search_fields = ('booking_reference', 'customer_name', 'customer_email', 'motorcycle__brand', 'motorcycle__model')
#     raw_id_fields = ('motorcycle', 'customer_user') # Use for ForeignKey/OneToOne fields if many instances

# If you have other models in the hire app, register them here.