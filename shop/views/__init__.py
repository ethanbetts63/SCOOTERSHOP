# core/views/__init__.py

from .auth import login_view, logout_view, register
from .main import index, service
from .motorcycle_list import NewMotorcycleListView, UsedMotorcycleListView, HireMotorcycleListView, new, used, hire
from .motorcycle_detail import MotorcycleDetailView, MotorcycleCreateView, MotorcycleUpdateView, MotorcycleDeleteView
from .information import about, contact, privacy, returns, security, terms
from .service_booking import (
    service_booking_start,
    service_booking_step1,
    service_booking_step2_authenticated,
    service_booking_step2_anonymous,
    service_booking_step3_authenticated,
    service_booking_step3_anonymous,
    service_booking_not_yet_confirmed_view,
)
from .dashboard import dashboard_index, settings_business_info, settings_hire_booking, settings_service_booking, settings_service_types, delete_service_type, edit_service_type, add_service_type, settings_visibility, settings_miscellaneous, edit_about_page
