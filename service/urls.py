# # SCOOTER_SHOP/service/urls.py

# from django.urls import path
# # Import service booking views from the service/views package
# # from .views import (
# #     booking_start,
# #     booking_step1,
# #     booking_step2_authenticated,
# #     booking_step3_authenticated,
# #     booking_step2_anonymous,
# #     booking_step3_anonymous,
# #     service_confirmed_view,
# #     # Removed the old booking_admin_view
# #     booking_admin_anon_view, # Import the new anonymous admin view
# #     booking_admin_user_view, # Import the new user admin view
# #     # Updated imports for renamed AJAX helper views
# #     get_user_details_for_admin,
# #     get_user_motorcycles_for_admin,
# #     get_motorcycle_details_for_admin,
# #     service,
# #     # Import the new AJAX view for available slots
# #     get_available_slots_ajax,

# # )

# dashboard views
    # path('service-bookings/', views.service_bookings_view, name='service_bookings'),
    # path('service-bookings/<int:pk>/', views.service_booking_details_view, name='service_booking_details'),
    # path('service-bookings/search/', views.service_booking_search_view, name='service_booking_search'),
    # path('service-bookings/json/', views.get_service_bookings_json, name='get_service_bookings_json'),



# app_name = 'service'
# urlpatterns = [
#     # Change 'service' to '' to match the base URL /service/
#     path('', service, name='service'),
#     # --- Service Booking Views ---
#     # Using '' here means /service/
#     # Updated URL name and view function reference
#     path('book/start/', booking_start, name='service_start'),
#     # Updated URL name and view function reference
#     path('book/step1/', booking_step1, name='service_step1'),
#     path('book/auth/step2/', booking_step2_authenticated, name='service_step2_authenticated'),
#     path('book/auth/step3/', booking_step3_authenticated, name='service_step3_authenticated'),
#     path('book/anon/step2/', booking_step2_anonymous, name='service_step2_anonymous'),
#     # Updated URL name and view function reference
#     path('book/anon/step3/', booking_step3_anonymous, name='service_step3_anonymous'),
#     path('book/confirmed/', service_confirmed_view, name='service_confirmed'),
#     path('book/admin/anon/', booking_admin_anon_view, name='admin_booking_anon'), # New URL for anonymous admin booking
#     path('book/admin/user/', booking_admin_user_view, name='admin_booking_user'), # New URL for user admin booking
#     path('service/get_user_details/<int:user_id>/', get_user_details_for_admin, name='get_user_details'),
#     path('service/get_user_motorcycles/<int:user_id>/', get_user_motorcycles_for_admin, name='get_user_motorcycles'),
#     path('service/get_motorcycle_details/<int:motorcycle_id>/', get_motorcycle_details_for_admin, name='get_motorcycle_details'),

#     # New AJAX endpoint for getting available time slots
#     path('book/ajax/available-slots/', get_available_slots_ajax, name='get_available_slots_ajax'),
# ]



# service/urls.py

app_name = 'service'

from django.urls import path
from service.views import user_views, admin_views

urlpatterns = [
    # User-facing service main page
    path('', user_views.service, name='service'),

    # User-facing booking flow steps
    path('service-book/step1/', user_views.Step1ServiceDetailsView.as_view(), name='service_book_step1'),
    path('service-book/step2/', user_views.Step2MotorcycleSelectionView.as_view(), name='service_book_step2'),
    path('service-book/step3/', user_views.Step3CustomerMotorcycleView.as_view(), name='service_book_step3'),
    path('service-book/step4/', user_views.Step4ServiceProfileView.as_view(), name='service_book_step4'),
    path('service-book/step5/', user_views.Step5PaymentChoiceAndTermsView.as_view(), name='service_book_step5'),
    path('service-book/step6/', user_views.Step6PaymentView.as_view(), name='service_book_step6'),
    path('service-book/step7/', user_views.Step7ConfirmationView.as_view(), name='service_book_step7'),

    # Admin-facing management
    path('service-booking-management/', admin_views.ServiceBookingManagementView.as_view(), name='service_booking_management'),
    path('service-booking-settings/', admin_views.ServiceBookingSettingsView.as_view(), name='service_booking_settings'),
    path('service-bookings/json/', admin_views.ServiceBookingJSONFeedView.as_view(), name='get_service_bookings_json'),
    
    path('blocked-dates/', admin_views.BlockedServiceDateManagementView.as_view(), name='blocked_service_dates_management'),
    path('blocked-dates/delete/<int:pk>/', admin_views.BlockedServiceDateDeleteView.as_view(), name='delete_blocked_service_date'),

    path('service-brands/', admin_views.ServiceBrandManagementView.as_view(), name='service_brands_management'),
    path('service-brands/delete/<int:pk>/', admin_views.ServiceBrandDeleteView.as_view(), name='delete_service_brand'),

    path('service-types/', admin_views.ServiceTypeManagementView.as_view(), name='service_types_management'),
    path('service-types/add/', admin_views.ServiceTypeCreateUpdateView.as_view(), name='add_service_type'), 
    path('service-types/edit/<int:pk>/', admin_views.ServiceTypeCreateUpdateView.as_view(), name='edit_service_type'),
    path('service-types/delete/<int:pk>/', admin_views.ServiceTypeDeleteView.as_view(), name='delete_service_type'),
]
