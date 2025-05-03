# service/views/__init__.py

# Imports for service booking views
from .booking import (
    booking_start, 
    booking_step1, 
    booking_step2_authenticated, 
    booking_step2_anonymous,
    booking_step3_authenticated,
    booking_step3_anonymous, 
    service_confirmed_view, 
)