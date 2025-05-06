# SCOOTER_SHOP/dashboard/urls.py

from django.urls import path
# Import dashboard views
from .views import (
    dashboard_index,
    service_bookings_view,
    service_booking_details_view, 
    service_bookings_day_view,
    edit_about_page,
    settings_business_info,
    settings_visibility,
    settings_service_booking,
    settings_hire_booking,
    settings_miscellaneous,
    settings_service_types,
    add_service_type,
    edit_service_type,
    delete_service_type
)

app_name = 'dashboard' # Set the app name for namespacing

urlpatterns = [
    # --- Dashboard Views ---
    # Using '' here means /dashboard/
    path('', dashboard_index, name='dashboard_index'),
    path('service-bookings/', service_bookings_view, name='service_bookings'),
    path('service-bookings/<int:year>/<int:month>/<int:day>/', service_bookings_day_view, name='service_bookings_day'),
    # Add the new URL pattern for service booking details
    path('service-bookings/<int:pk>/', service_booking_details_view, name='service_booking_details'),
    path('edit-about/', edit_about_page, name='edit_about_page'),

    # --- Dashboard Settings Views ---
    path('settings/business-info/', settings_business_info, name='settings_business_info'),
    path('settings/visibility/', settings_visibility, name='settings_visibility'),
    path('settings/service-booking/', settings_service_booking, name='settings_service_booking'),
    path('settings/hire-booking/', settings_hire_booking, name='settings_hire_booking'),
    path('settings/miscellaneous/', settings_miscellaneous, name='settings_miscellaneous'),

    # --- Dashboard Service Type Management Views ---
    path('settings/service-types/', settings_service_types, name='settings_service_types'),
    path('settings/service-types/add/', add_service_type, name='add_service_type'),
    path('settings/service-types/edit/<int:pk>/', edit_service_type, name='edit_service_type'),
    path('settings/service-types/delete/<int:pk>/', delete_service_type, name='delete_service_type'),
]
