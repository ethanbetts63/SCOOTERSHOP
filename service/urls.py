# SCOOTER_SHOP/service/urls.py

from django.urls import path
# Import service booking views
from .views import (
    service_booking_start, service_booking_step1,
    service_booking_step2_authenticated, service_booking_step3_authenticated,
    service_booking_step2_anonymous, service_booking_step3_anonymous,
    service_booking_not_yet_confirmed_view
) # Assuming these views are in service/views.py


app_name = 'service' # Set the app name for namespacing

urlpatterns = [
    # --- Service Booking Views ---
    # Using '' here means /service/
    path('book/start/', service_booking_start, name='service_booking_start'),
    path('book/step1/', service_booking_step1, name='service_booking_step1'), # Changed from auth/step1 as the split is handled internally

    # Authenticated Flow
    path('book/auth/step2/', service_booking_step2_authenticated, name='service_booking_step2_authenticated'),
    path('book/auth/step3/', service_booking_step3_authenticated, name='service_booking_step3_authenticated'),

    # Anonymous Flow
    path('book/anon/step2/', service_booking_step2_anonymous, name='service_booking_step2_anonymous'),
    path('book/anon/step3/', service_booking_step3_anonymous, name='service_booking_step3_anonymous'),

    path('book/confirmed/', service_booking_not_yet_confirmed_view, name='service_booking_not_yet_confirmed'),

    # Add a base service page if needed, maybe listing service types?
    # path('', views.service_type_list, name='service_types'),
]