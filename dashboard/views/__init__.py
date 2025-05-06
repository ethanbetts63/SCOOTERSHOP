# dashboard/views/__init__.py

# Imports for dashboard and settings views (formerly in dashboard.py)
from .dashboard import (
    dashboard_index,
    service_bookings_view,
    service_booking_details_view,
    service_bookings_day_view, # Added this import
    settings_business_info,
    settings_hire_booking,
    settings_service_booking,
    settings_service_types,
    delete_service_type,
    edit_service_type,
    add_service_type,
    settings_visibility,
    settings_miscellaneous,
    edit_about_page,
)