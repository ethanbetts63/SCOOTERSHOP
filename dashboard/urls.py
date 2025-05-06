# SCOOTER_SHOP/dashboard/urls.py

from django.urls import path

# Import views from the dashboard.views package
# Import non-booking views from dashboard.py (via __init__.py)
from .views.dashboard import (
    dashboard_index,
    edit_about_page,
    settings_business_info,
    settings_visibility,
    settings_service_booking,
    settings_hire_booking,
    settings_miscellaneous,
    settings_service_types,
    add_service_type,
    edit_service_type,
    delete_service_type,
)

# Import booking views from the new bookings.py file (via __init__.py)
from .views.bookings import (
    service_bookings_view,
    service_booking_details_view,
    get_bookings_json, 
)


app_name = 'dashboard' # Set the app name for namespacing

urlpatterns = [
    # --- Dashboard Views ---
    path('', dashboard_index, name='dashboard_index'),

    # --- Booking Views (Now imported from bookings.py) ---
    # The main calendar view (will use FullCalendar)
    path('service-bookings/', service_bookings_view, name='service_bookings'),
    # The detail view for a single booking
    path('service-bookings/<int:pk>/', service_booking_details_view, name='service_booking_details'),

    # --- New URL pattern for the FullCalendar JSON feed ---
    path('bookings/json/', get_bookings_json, name='get_bookings_json'),


    path('edit-about/', edit_about_page, name='edit_about_page'),

    # --- Dashboard Settings Views (Remain imported from dashboard.py) ---
    path('settings/business-info/', settings_business_info, name='settings_business_info'),
    path('settings/visibility/', settings_visibility, name='settings_visibility'),
    path('settings/service-booking/', settings_service_booking, name='settings_service_booking'),
    path('settings/hire-booking/', settings_hire_booking, name='settings_hire_booking'),
    path('settings/miscellaneous/', settings_miscellaneous, name='settings_miscellaneous'),

    # --- Dashboard Service Type Management Views (Remain imported from dashboard.py) ---
    path('settings/service-types/', settings_service_types, name='settings_service_types'),
    path('settings/service-types/add/', add_service_type, name='add_service_type'),
    path('settings/service-types/edit/<int:pk>/', edit_service_type, name='edit_service_type'),
    path('settings/service-types/delete/<int:pk>/', delete_service_type, name='delete_service_type'),
]