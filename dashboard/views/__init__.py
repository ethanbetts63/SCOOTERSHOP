# dashboard/views/__init__.py

# Imports for dashboard and settings views (formerly in dashboard.py)
from .dashboard import (
    dashboard_index,
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
    get_bookings_json,
    is_staff_check,
    service_booking_search_view, # Import the new search view
)