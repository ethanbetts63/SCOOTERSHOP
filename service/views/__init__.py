# service/views/__init__.py

# Imports for general booking views (booking_start, service_confirmed_view)
from .booking import (
    booking_start,
    service_confirmed_view,
)

# Imports for booking step 1 view
from .booking_step1 import (
    booking_step1,
)

# Imports for booking step 2 views
from .booking_step2 import (
    booking_step2_authenticated,
    booking_step2_anonymous,
)

# Imports for booking step 3 views
from .booking_step3 import (
    booking_step3_authenticated,
    booking_step3_anonymous,
)

# Import admin booking view
from .booking_admin import ( # Added this import block
    booking_admin_view,
    get_user_motorcycles,
    get_user_details,
    get_motorcycle_details,
)

# Import other service views (like the 'service' view if it exists)
from .service import (
    service
)