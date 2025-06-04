# dashboard/forms/__init__.py

# Import all your forms here so they can be imported directly from dashboard.forms
from .about_page_content_form import AboutPageContentForm
from .blocked_hire_date_form import BlockedHireDateForm
from .business_info_form import BusinessInfoForm
from .hire_booking_settings_form import HireBookingSettingsForm
from .visibility_settings_form import VisibilitySettingsForm
from .driver_profile_form import DriverProfileForm

# You can also define __all__ to explicitly list what is exported
__all__ = [
    'AboutPageContentForm',
    'BlockedHireDateForm',
    'BlockedServiceDateForm',
    'BusinessInfoForm',
    'HireBookingSettingsForm',
    'ServiceBookingSettingsForm',
    'ServiceBrandForm',
    'ServiceTypeForm',
    'VisibilitySettingsForm',
]
