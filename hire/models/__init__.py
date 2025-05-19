# hire/models/__init__.py

from .driver_profile import DriverProfile
from .hire_addon import AddOn          # Import the new AddOn model
from .hire_packages import Package     # This imports Package which now correctly imports AddOn
from .hire_booking import HireBooking  # This imports HireBooking which now correctly imports Package and BookingAddOn
from .hire_addons import BookingAddOn  # Import the BookingAddOn model (assuming this file is named hire_addons.py)
from .temp_hire_booking import TempHireBooking
from .temp_booking_addon import TempBookingAddOn

# You can add __all__ for explicit export if desired
__all__ = [
    'HireSettings',
    'DriverProfile',
    'AddOn',
    'Package',
    'BookingAddOn',
    'HireBooking',
    'TempHireBooking',
    'TempBookingAddOn'
]