# core/views/__init__.py

from .auth import login_view, logout_view, register
from .main import index, service
from .motorcycle_list import NewMotorcycleListView, UsedMotorcycleListView, HireMotorcycleListView, new, used, hire
from .motorcycle_detail import MotorcycleDetailView, MotorcycleCreateView, MotorcycleUpdateView, MotorcycleDeleteView
from .information import about, contact, privacy, returns, security, terms
from .service_booking import (
    service_booking_start,
    service_booking_step1_authenticated,
    service_booking_step1_anonymous,
    service_booking_step2_authenticated,
    service_booking_step2_anonymous,
    service_booking_step3_authenticated,
    service_booking_step3_anonymous,
    service_booking_not_yet_confirmed_view,
)
from .dashboard import dashboard_index, settings_business_info, settings_hire_booking, settings_service_booking, settings_service_types, delete_service_type, edit_service_type, add_service_type, settings_visibility, settings_miscellaneous, edit_about_page

# You can optionally define __all__ to explicitly list what should be imported
__all__ = [
    'login_view', 'logout_view', 'register',
    'index', 'service',
    'NewMotorcycleListView', 'UsedMotorcycleListView', 'HireMotorcycleListView', 'new', 'used', 'hire',
    'MotorcycleDetailView', 'MotorcycleCreateView', 'MotorcycleUpdateView', 'MotorcycleDeleteView',
    'about', 'contact', 'privacy', 'returns', 'security', 'terms',
    'service_booking_start', 'service_booking_step1', 'service_booking_step2', 'service_booking_step3', 'service_booking_not_yet_confirmed_view',
    'dashboard_index', 'settings_business_info', 'settings_hire_booking', 'settings_service_booking', 'settings_service_types', 'delete_service_type', 'edit_service_type', 'add_service_type', 'settings_visibility', 'settings_miscellaneous', 'edit_about_page',
]

# Note: Utility functions like get_featured_motorcycles are not typically
# imported into __init__.py unless they are intended for public use outside the views package.
# We will import them directly where they are needed within the views files.