# SCOOTER_SHOP/service/urls.py

from django.urls import path
# Import service booking views from the service/views package
from .views import (
    booking_start,
    booking_step1,
    booking_step2_authenticated,
    booking_step3_authenticated,
    booking_step2_anonymous,
    booking_step3_anonymous,
    service_confirmed_view,
    # Removed the old booking_admin_view
    booking_admin_anon_view, # Import the new anonymous admin view
    booking_admin_user_view, # Import the new user admin view
    # Updated imports for renamed AJAX helper views
    get_user_details_for_admin,
    get_user_motorcycles_for_admin,
    get_motorcycle_details_for_admin,
    service,
    # Import the new AJAX view for available slots
    get_available_slots_ajax,

)



app_name = 'service'
urlpatterns = [
    # Change 'service' to '' to match the base URL /service/
    path('', service, name='service'),
    # --- Service Booking Views ---
    # Using '' here means /service/
    # Updated URL name and view function reference
    path('book/start/', booking_start, name='service_start'),
    # Updated URL name and view function reference
    path('book/step1/', booking_step1, name='service_step1'),

    # Authenticated Flow
    # Updated URL name and view function reference
    path('book/auth/step2/', booking_step2_authenticated, name='service_step2_authenticated'),
    # Updated URL name and view function reference
    path('book/auth/step3/', booking_step3_authenticated, name='service_step3_authenticated'),

    # Anonymous Flow
    # Updated URL name and view function reference
    path('book/anon/step2/', booking_step2_anonymous, name='service_step2_anonymous'),
    # Updated URL name and view function reference
    path('book/anon/step3/', booking_step3_anonymous, name='service_step3_anonymous'),

    # Updated URL name and view function reference
    path('book/confirmed/', service_confirmed_view, name='service_confirmed'),

    # Admin Booking Views
    path('book/admin/anon/', booking_admin_anon_view, name='admin_booking_anon'), # New URL for anonymous admin booking
    path('book/admin/user/', booking_admin_user_view, name='admin_booking_user'), # New URL for user admin booking

    # Updated AJAX Helper View URLs
    path('service/get_user_details/<int:user_id>/', get_user_details_for_admin, name='get_user_details'),
    path('service/get_user_motorcycles/<int:user_id>/', get_user_motorcycles_for_admin, name='get_user_motorcycles'),
    path('service/get_motorcycle_details/<int:motorcycle_id>/', get_motorcycle_details_for_admin, name='get_motorcycle_details'),

    # New AJAX endpoint for getting available time slots
    path('book/ajax/available-slots/', get_available_slots_ajax, name='get_available_slots_ajax'),
]