# service/urls.py
from django.urls import path
from service.views import (
    user_views,
    admin_views, # Ensure admin_views is imported here
)
from service.ajax import (
    ajax_get_available_dropoff_times_for_date,
    ajax_get_available_service_dates,
    ajax_get_customer_motorcycle_details,
    ajax_get_customer_motorcycles,
    ajax_get_service_profile_details,
    ajax_search_service_profiles,
    ajax_admin_booking_precheck
)

app_name = 'service'

urlpatterns = [
    # User-facing service main page
    path('', user_views.service, name='service'),

    # User-facing booking flow steps
    # CORRECTED: Referencing the function within the module
    path('service-book/get-available-times/', ajax_get_available_dropoff_times_for_date.get_available_dropoff_times_for_date, name='get_available_dropoff_times_for_date'),
    path('service-book/step1/', user_views.Step1ServiceDetailsView.as_view(), name='service_book_step1'),
    path('service-book/step2/', user_views.Step2MotorcycleSelectionView.as_view(), name='service_book_step2'),
    path('service-book/step3/', user_views.Step3CustomerMotorcycleView.as_view(), name='service_book_step3'),
    path('service-book/step4/', user_views.Step4ServiceProfileView.as_view(), name='service_book_step4'),
    path('service-book/step5/', user_views.Step5PaymentDropoffAndTermsView.as_view(), name='service_book_step5'),
    path('service-book/step6/', user_views.Step6PaymentView.as_view(), name='service_book_step6'),

    # Step 7: Confirmation page
    path('service-book/step7/', user_views.Step7ConfirmationView.as_view(), name='service_book_step7'),

    # NEW: AJAX endpoint for checking booking status
    path('service-book/status-check/', user_views.Step7StatusCheckView.as_view(), name='service_booking_status_check'),


    # Admin-facing management
    path('service-booking-management/', admin_views.ServiceBookingManagementView.as_view(), name='service_booking_management'),
    # service/urls.py
    path('service-booking-management/create-booking/', admin_views.AdminBookingCreateView.as_view(), name='admin_create_service_booking'),

    path('service-settings/', admin_views.ServiceSettingsView.as_view(), name='service_settings'),
    path('service-bookings/json/', admin_views.ServiceBookingJSONFeedView.as_view(), name='get_service_bookings_json'),

    path('blocked-dates/', admin_views.BlockedServiceDateManagementView.as_view(), name='blocked_service_dates_management'),
    path('blocked-dates/delete/<int:pk>/', admin_views.BlockedServiceDateDeleteView.as_view(), name='delete_blocked_service_date'),

    path('service-brands/', admin_views.ServiceBrandManagementView.as_view(), name='service_brands_management'),
    path('service-brands/delete/<int:pk>/', admin_views.ServiceBrandDeleteView.as_view(), name='delete_service_brand'),

    path('service-types/', admin_views.ServiceTypeManagementView.as_view(), name='service_types_management'),
    path('service-types/add/', admin_views.ServiceTypeCreateUpdateView.as_view(), name='add_service_type'),
    path('service-types/edit/<int:pk>/', admin_views.ServiceTypeCreateUpdateView.as_view(), name='edit_service_type'),
    path('service-types/delete/<int:pk>/', admin_views.ServiceTypeDeleteView.as_view(), name='delete_service_type'),

    # ADMIN SERVICE PROFILE MANAGEMENT
    path('admin/service-profiles/', admin_views.ServiceProfileManagementView.as_view(), name='admin_service_profiles'),
    path('admin/service-profiles/create/', admin_views.ServiceProfileCreateUpdateView.as_view(), name='admin_create_service_profile'),
    path('admin/service-profiles/edit/<int:pk>/', admin_views.ServiceProfileCreateUpdateView.as_view(), name='admin_edit_service_profile'),
    path('admin/service-profiles/delete/<int:pk>/', admin_views.ServiceProfileDeleteView.as_view(), name='admin_delete_service_profile'),

    # ADMIN CUSTOMER MOTORCYCLE MANAGEMENT
    path('admin/customer-motorcycles/', admin_views.CustomerMotorcycleManagementView.as_view(), name='admin_customer_motorcycle_management'),
    path('admin/customer-motorcycles/create/', admin_views.CustomerMotorcycleCreateUpdateView.as_view(), name='admin_create_customer_motorcycle'),
    path('admin/customer-motorcycles/edit/<int:pk>/', admin_views.CustomerMotorcycleCreateUpdateView.as_view(), name='admin_edit_customer_motorcycle'),
    path('admin/customer-motorcycles/delete/<int:pk>/', admin_views.CustomerMotorcycleDeleteView.as_view(), name='admin_delete_customer_motorcycle'),
# --- NEW AJAX Endpoints for Admin Booking Flow ---
    # Customer Profile Search & Details
    path(
        'admin/api/search-customer/',
        ajax_search_service_profiles.search_customer_profiles_ajax,
        name='admin_api_search_customer'
    ),
    path(
        'admin/api/get-customer-details/<int:profile_id>/',
        ajax_get_service_profile_details.get_service_profile_details_ajax,
        name='admin_api_get_customer_details'
    ),

    # Customer Motorcycle List & Details
    path(
        'admin/api/customer-motorcycles/<int:profile_id>/',
        ajax_get_customer_motorcycles.get_customer_motorcycles_ajax,
        name='admin_api_customer_motorcycles'
    ),
    path(
        'admin/api/get-motorcycle-details/<int:motorcycle_id>/',
        ajax_get_customer_motorcycle_details.get_motorcycle_details_ajax,
        name='admin_api_get_motorcycle_details'
    ),

    # Service Date Availability
    path(
        'admin/api/service-date-availability/',
        ajax_get_available_service_dates.get_service_date_availability_ajax,
        name='admin_api_service_date_availability'
    ),

    # Drop-off Time Availability (Next, we'll create this file/view)
    # CORRECTED: Referencing the function within the module with the correct function name
    path(
        'admin/api/dropoff-time-availability/',
        ajax_get_available_dropoff_times_for_date.get_available_dropoff_times_for_date,
        name='admin_api_dropoff_time_availability'
    ),

    # NEW: Admin Booking Pre-check AJAX endpoint
    path('admin/api/booking-precheck/', ajax_admin_booking_precheck.admin_booking_precheck_ajax, name='admin_api_booking_precheck'),

]
