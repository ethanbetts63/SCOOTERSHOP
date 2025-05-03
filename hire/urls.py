# SCOOTER_SHOP/hire/urls.py

from django.urls import path
# Import hire booking views
# from .views import hire_booking_view, etc. # You'll define these views


app_name = 'hire' # Set the app name for namespacing

urlpatterns = [
    # --- Hire Booking Views ---
    # You'll need to add your hire booking URL patterns here
    # Example:
    # path('book/', hire_booking_view, name='hire_booking_start'),
    # path('book/confirm/', hire_booking_confirm, name='hire_booking_confirm'),
    # path('bookings/', user_hire_bookings, name='user_hire_bookings'), # For logged-in users

    # The 'hire/' path was in your core urls, you might want to move the view it points to
    # into this app, or keep it in 'inventory' if it's just a list of bikes for hire.
    # If the 'hire' view in your core urls showed bikes available for hire,
    # you might move that to the 'inventory' app's urls.
    # If this app is specifically for the booking process *after* selecting a bike,
    # then its URLs would start with something like 'book/'
]