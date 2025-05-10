# dashboard/views/__init__.py

# Imports for dashboard and settings views
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
    edit_about_page,
    toggle_service_type_active_status, 
    service_brands_management,
    delete_service_brand
)

# Import booking views and the helper function from the new bookings.py file
from .bookings import (
    service_bookings_view,
    service_booking_details_view,
    get_bookings_json,
    service_booking_search_view, 
)