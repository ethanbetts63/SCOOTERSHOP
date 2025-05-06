# dashboard/views/__init__.py

# Imports for dashboard and settings views (formerly in dashboard.py)
from .dashboard import (
    dashboard_index,
    # Removed booking views imports from here:
    # service_bookings_view,
    # service_booking_details_view,
    # service_bookings_day_view,
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

# Import booking views and the helper function from the new bookings.py file
from .bookings import (
    service_bookings_view,
    service_booking_details_view,
    service_bookings_day_view,
    get_bookings_json, 
    is_staff_check,
)
