# dashboard/views/__init__.py

# Imports for dashboard and settings views
from .index import dashboard_index
from .settings_business_info import settings_business_info
from .settings_hire_booking import settings_hire_booking
from .settings_service_booking import settings_service_booking
from .blocked_service_dates_management import blocked_service_dates_management
from .delete_blocked_service_date import delete_blocked_service_date
from .blocked_hire_dates_management import blocked_hire_dates_management
from .delete_blocked_hire_date import delete_blocked_hire_date
from .settings_service_types import settings_service_types
from .delete_service_type import delete_service_type
from .edit_service_type import edit_service_type
from .add_service_type import add_service_type
from .settings_visibility import settings_visibility
from .edit_about_page import edit_about_page
from .toggle_service_type_active_status import toggle_service_type_active_status
from .service_brands_management import service_brands_management
from .delete_service_brand import delete_service_brand


# Import booking views from the service_bookings.py file 
from .service_bookings import (
    service_bookings_view,
    service_booking_details_view,
    get_service_bookings_json,
    service_booking_search_view,
)

from .hire_bookings import (
    hire_bookings_view, 
    hire_booking_details_view, 
    get_hire_bookings_json, 
    hire_booking_search_view
)