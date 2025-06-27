# SCOOTER_SHOP/inventory/urls.py

from django.urls import path

from .views.user_views import (
    motorcycle_list_view,
    initiate_sales_booking_process_view,
    step1_sales_profile,
    step2_booking_details,
    step3_payment_view,
    step4_confirmation_view,
    user_motorcycle_details_view,
)

from .views.admin_views import (
    admin_motorcycle_details_view,
    blocked_sales_date_management_view,
    blocked_sales_date_create_update_view,
    inventory_management_view,
    inventory_settings_view,
    motorcycle_create_update_view,
    sales_booking_action_view,
    sales_booking_create_update_view,
    sales_booking_details_view,
    sales_bookings_management_view,
    sales_profile_create_update_view,
    sales_profile_details_view,
    sales_profile_management_view,
    delete_motorcycle,
    delete_blocked_sales_date,
    delete_sales_booking,
    delete_sales_profile,
    sales_FAQ_management_view,
    sales_FAQ_create_update_view,
    sales_FAQ_details_view,
    sales_FAQ_delete_view,
)

from .ajax import (
    get_motorcycle_list,
    get_available_appointment_times_for_date,
    ajax_get_payment_status,
    ajax_get_sales_booking_details,
    ajax_search_motorcycles,
    ajax_get_motorcycle_details,
    ajax_search_sales_profiles,
    ajax_get_sales_profile_details,
    ajax_sales_booking_precheck,
    ajax_motorcycle_availability_check, # Import the new view
)

app_name = 'inventory'

urlpatterns = [
    # ... (existing user and admin motorcycle URLs)
    path('motorcycles/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'all'}, name='all'),
    path('motorcycles/new/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'new'}, name='new'),
    path('motorcycles/used/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'used'}, name='used'),
    path('motorcycles/<int:pk>/', user_motorcycle_details_view.UserMotorcycleDetailsView.as_view(), name='motorcycle-detail'),
    path('motorcycles/<int:pk>/initiate_booking/', initiate_sales_booking_process_view.InitiateBookingProcessView.as_view(), name='initiate_booking'),
    path('booking/your-details/', step1_sales_profile.Step1SalesProfileView.as_view(), name='step1_sales_profile'),
    path('booking/details-and-appointment/', step2_booking_details.Step2BookingDetailsView.as_view(), name='step2_booking_details_and_appointment'),
    path('booking/payment/', step3_payment_view.Step3PaymentView.as_view(), name='step3_payment'),
    path('booking/confirmation/', step4_confirmation_view.Step4ConfirmationView.as_view(), name='step4_confirmation'),
    path('admin/settings/', inventory_settings_view.InventorySettingsView.as_view(), name='inventory_settings'),
    path('admin/inventory/', inventory_management_view.InventoryManagementView.as_view(), name='admin_inventory_management'),
    path('admin/inventory/new/', inventory_management_view.InventoryManagementView.as_view(), {'condition_slug': 'new'}, name='admin_new_motorcycle_management'),
    path('admin/inventory/used/', inventory_management_view.InventoryManagementView.as_view(), {'condition_slug': 'used'}, name='admin_used_motorcycle_management'),
    path('admin/motorcycles/create/', motorcycle_create_update_view.MotorcycleCreateUpdateView.as_view(), name='admin_motorcycle_create'),
    path('admin/motorcycles/<int:pk>/update/', motorcycle_create_update_view.MotorcycleCreateUpdateView.as_view(), name='admin_motorcycle_update'),
    path('admin/motorcycles/<int:pk>/delete/', delete_motorcycle.MotorcycleDeleteView.as_view(), name='admin_motorcycle_delete'),
    path('admin/motorcycles/<int:pk>/details/', admin_motorcycle_details_view.AdminMotorcycleDetailsView.as_view(), name='admin_motorcycle_details'),
    path('admin/blocked-sales-dates/', blocked_sales_date_management_view.BlockedSalesDateManagementView.as_view(), name='blocked_sales_date_management'),
    path('admin/blocked-sales-dates/create/', blocked_sales_date_create_update_view.BlockedSalesDateCreateUpdateView.as_view(), name='blocked_sales_date_create'),
    path('admin/blocked-sales-dates/<int:pk>/update/', blocked_sales_date_create_update_view.BlockedSalesDateCreateUpdateView.as_view(), name='blocked_sales_date_update'),
    path('admin/blocked-sales-dates/<int:pk>/delete/', delete_blocked_sales_date.BlockedSalesDateDeleteView.as_view(), name='admin_blocked_sales_date_delete'),
    path('admin/sales-bookings/', sales_bookings_management_view.SalesBookingsManagementView.as_view(), name='sales_bookings_management'),
    path('admin/sales-bookings/create/', sales_booking_create_update_view.SalesBookingCreateUpdateView.as_view(), name='sales_booking_create'),
    path('admin/sales-bookings/<int:pk>/update/', sales_booking_create_update_view.SalesBookingCreateUpdateView.as_view(), name='sales_booking_update'),
    path('admin/sales-bookings/<int:pk>/delete/', delete_sales_booking.SalesBookingDeleteView.as_view(), name='admin_sales_booking_delete'),
    path('admin/sales-bookings/<int:pk>/details/', sales_booking_details_view.SalesBookingDetailsView.as_view(), name='sales_booking_details'),
    path('admin/sales-bookings/<int:pk>/<str:action_type>/', sales_booking_action_view.SalesBookingActionView.as_view(), name='admin_sales_booking_action'),
    path('admin/sales-profiles/', sales_profile_management_view.SalesProfileManagementView.as_view(), name='sales_profile_management'),
    path('admin/sales-profiles/create/', sales_profile_create_update_view.SalesProfileCreateUpdateView.as_view(), name='sales_profile_create'),
    path('admin/sales-profiles/<int:pk>/update/', sales_profile_create_update_view.SalesProfileCreateUpdateView.as_view(), name='sales_profile_update'),
    path('admin/sales-profiles/<int:pk>/delete/', delete_sales_profile.SalesProfileDeleteView.as_view(), name='admin_sales_profile_delete'),
    path('admin/sales-profiles/<int:pk>/details/', sales_profile_details_view.SalesProfileDetailsView.as_view(), name='sales_profile_details'),

    # Sales FAQ Management
    path('admin/sales-faqs/', sales_FAQ_management_view.SalesFAQManagementView.as_view(), name='sales_faq_management'),
    path('admin/sales-faqs/create/', sales_FAQ_create_update_view.SalesFAQCreateUpdateView.as_view(), name='sales_faq_create'),
    path('admin/sales-faqs/<int:pk>/update/', sales_FAQ_create_update_view.SalesFAQCreateUpdateView.as_view(), name='sales_faq_update'),
    path('admin/sales-faqs/<int:pk>/delete/', sales_FAQ_delete_view.SalesFAQDeleteView.as_view(), name='sales_faq_delete'),
    path('admin/sales-faqs/<int:pk>/details/', sales_FAQ_details_view.SalesFAQDetailsView.as_view(), name='sales_faq_details'),


    # AJAX Endpoints
    path('ajax/get-motorcycle-list/', get_motorcycle_list, name='ajax-get-motorcycle-list'),
    path('ajax/get_appointment_times/', get_available_appointment_times_for_date, name='ajax_get_appointment_times'),
    path('ajax/payment-status-check/', ajax_get_payment_status.GetPaymentStatusView.as_view(), name='ajax_sales_payment_status_check'),
    path('ajax/sales-booking-details/<int:pk>/', ajax_get_sales_booking_details.get_sales_booking_details_json, name='api_sales_booking_details'),
    path('ajax/admin/search-motorcycles/', ajax_search_motorcycles.search_motorcycles_ajax, name='admin_api_search_motorcycles'),
    path('ajax/admin/get-motorcycle-details/<int:pk>/', ajax_get_motorcycle_details.get_motorcycle_details_ajax, name='admin_api_get_motorcycle_details'),
    path('ajax/admin/search-sales-profiles/', ajax_search_sales_profiles.search_sales_profiles_ajax, name='admin_api_search_sales_profiles'),
    path('ajax/admin/get-sales-profile-details/<int:pk>/', ajax_get_sales_profile_details.get_sales_profile_details_ajax, name='admin_api_get_sales_profile_details'),
    path('ajax/admin/sales-booking-precheck/', ajax_sales_booking_precheck.sales_booking_precheck_ajax, name='admin_api_sales_booking_precheck'),
    path('ajax/check-motorcycle-availability/', ajax_motorcycle_availability_check.check_motorcycle_availability, name='ajax_check_motorcycle_availability'), # New AJAX URL
]
