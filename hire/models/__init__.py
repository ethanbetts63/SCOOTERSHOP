# This file makes the 'models' directory a Python package.

# Import the HireBooking model
from .hire_booking import HireBooking

# Import the DriverProfile model
from .driver_profile import DriverProfile

# Import Package and AddOn models
from .hire_packages import Package
from .hire_addons import AddOn


# You can optionally define __all__ to specify what is exported
__all__ = [
    'HireBooking',
    'DriverProfile', 
    'Package',
    'AddOn',
]

