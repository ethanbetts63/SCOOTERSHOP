# dashboard/views/__init__.py

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
from .add_addon_view import AddEditAddOnView
from .delete_addon_view import delete_addon
from .settings_business_info import *
from .settings_hire_booking import *
from .index import *
from .settings_hire_addons import settings_hire_addons
from .settings_hire_packages import HirePackagesSettingsView
from .add_edit_package_view import AddEditPackageView
from .delete_package_view import DeletePackageView
from .hire_booking_management import *
from hire_booking_details_view import *
from hire_booking_search_view import *

# Import booking views from the service_bookings.py file 
from .service_bookings import (
    service_bookings_view,
    service_booking_details_view,
    get_service_bookings_json,
    service_booking_search_view,
)

