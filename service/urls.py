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
    booking_admin_view,
    get_user_motorcycles,
    get_user_details,
    service,

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

    # Admin Booking View
    path('book/admin/', booking_admin_view, name='admin_booking'), # Added this URL pattern
    path('admin/get_user_details/<int:user_id>/', get_user_details, name='get_user_details'),
    path('admin/get_user_motorcycles/<int:user_id>/', get_user_motorcycles, name='get_user_motorcycles'),
]