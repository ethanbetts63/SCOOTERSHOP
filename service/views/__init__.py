# service/views/__init__.py

# Imports for service booking views 
from .booking import ( # Renamed service_booking.py to booking.py for simplicity
    service_booking_start,
    service_booking_step1,
    service_booking_step2_authenticated,
    service_booking_step2_anonymous,
    service_booking_step3_authenticated,
    service_booking_step3_anonymous,
    service_booking_not_yet_confirmed_view,
)
