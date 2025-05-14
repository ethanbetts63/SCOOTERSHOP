# This file makes the 'models' directory a Python package.

# Import each model from its respective file so they can be accessed directly
# from 'hire.models'.

# Import the HireBooking model (assuming the one in hire_packages.py is the correct one)
from .hire_booking import HireBooking

# # Import Package and AddOn models
# # Assuming Package is defined in hire_packages.py
# from .hire_packages import Package
# # Assuming AddOn is defined in a separate file named hire_addons.py
# from .hire_addons import AddOn


# You can optionally define __all__ to specify what is exported
__all__ = [
    'HireBooking',
    'Package',
    'AddOn',
]
