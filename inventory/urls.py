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
    inventory_management_view, # Keep this import for the single view
    inventory_settings_view,
    motorcycle_create_update_view,
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
)

from .ajax import (
    get_motorcycle_list,
    get_available_appointment_times_for_date,
    ajax_get_payment_status
)


app_name = 'inventory'

urlpatterns = [
    # Motorcycle List View
    path('motorcycles/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'all'}, name='all'),
    path('motorcycles/new/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'new'}, name='new'),
    path('motorcycles/used/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'used'}, name='used'),

    # Motorcycle Details View for Users
    path('motorcycles/<int:pk>/', user_motorcycle_details_view.UserMotorcycleDetailsView.as_view(), name='motorcycle-detail'),
    # User Flow
    path('motorcycles/<int:pk>/initiate_booking/', initiate_sales_booking_process_view.InitiateBookingProcessView.as_view(), name='initiate_booking'),
    path('booking/your-details/', step1_sales_profile.Step1SalesProfileView.as_view(), name='step1_sales_profile'),
    path('booking/details-and-appointment/', step2_booking_details.Step2BookingDetailsView.as_view(), name='step2_booking_details_and_appointment'),
    path('booking/payment/', step3_payment_view.Step3PaymentView.as_view(), name='step3_payment'),
    path('booking/confirmation/', step4_confirmation_view.Step4ConfirmationView.as_view(), name='step4_confirmation'),

    # Admin Views
    path('admin/settings/', inventory_settings_view.InventorySettingsView.as_view(), name='inventory_settings'),
    path('admin/inventory/', inventory_management_view.InventoryManagementView.as_view(), name='admin_inventory_management'),
    path('admin/inventory/new/', inventory_management_view.InventoryManagementView.as_view(), {'condition_slug': 'new'}, name='admin_new_motorcycle_management'),
    path('admin/inventory/used/', inventory_management_view.InventoryManagementView.as_view(), {'condition_slug': 'used'}, name='admin_used_motorcycle_management'),
    
    path('admin/motorcycles/create/', motorcycle_create_update_view.MotorcycleCreateUpdateView.as_view(), name='admin_motorcycle_create'),
    path('admin/motorcycles/<int:pk>/update/', motorcycle_create_update_view.MotorcycleCreateUpdateView.as_view(), name='admin_motorcycle_update'),
    path('admin/motorcycles/<int:pk>/delete/', delete_motorcycle.MotorcycleDeleteView.as_view(), name='admin_motorcycle_delete'),
    path('admin/motorcycles/<int:pk>/details/', admin_motorcycle_details_view.AdminMotorcycleDetailsView.as_view(), name='admin_motorcycle_details'),

    # Blocked Sales Date Management
    path('admin/blocked-sales-dates/', blocked_sales_date_management_view.BlockedSalesDateManagementView.as_view(), name='blocked_sales_date_management'),
    path('admin/blocked-sales-dates/create/', blocked_sales_date_create_update_view.BlockedSalesDateCreateUpdateView.as_view(), name='blocked_sales_date_create_update'), # New path for create
    path('admin/blocked-sales-dates/<int:pk>/update/', blocked_sales_date_create_update_view.BlockedSalesDateCreateUpdateView.as_view(), name='blocked_sales_date_create_update'), # New path for update (re-uses same name)
    path('admin/blocked-sales-dates/<int:pk>/delete/', delete_blocked_sales_date.BlockedSalesDateDeleteView.as_view(), name='admin_blocked_sales_date_delete'),


    # Sales Booking Management
    path('admin/sales-bookings/', sales_bookings_management_view.SalesBookingsManagementView.as_view(), name='sales_bookings_management'),
    path('admin/sales-bookings/create/', sales_booking_create_update_view.SalesBookingCreateUpdateView.as_view(), name='sales_booking_create_update'),
    path('admin/sales-bookings/<int:pk>/update/', sales_booking_create_update_view.SalesBookingCreateUpdateView.as_view(), name='sales_booking_create_update'),
    path('admin/sales-bookings/<int:pk>/delete/', delete_sales_booking.SalesBookingDeleteView.as_view(), name='admin_sales_booking_delete'),
    path('admin/sales-bookings/<int:pk>/details/', sales_booking_details_view.SalesBookingDetailsView.as_view(), name='sales_booking_details'),


    # Sales Profile Management
    path('admin/sales-profiles/', sales_profile_management_view.SalesProfileManagementView.as_view(), name='sales_profile_management'),
    path('admin/sales-profiles/create/', sales_profile_create_update_view.SalesProfileCreateUpdateView.as_view(), name='sales_profile_create_update'),
    path('admin/sales-profiles/<int:pk>/update/', sales_profile_create_update_view.SalesProfileCreateUpdateView.as_view(), name='sales_profile_create_update'),
    path('admin/sales-profiles/<int:pk>/delete/', delete_sales_profile.SalesProfileDeleteView.as_view(), name='admin_sales_profile_delete'),
    path('admin/sales-profiles/<int:pk>/details/', sales_profile_details_view.SalesProfileDetailsView.as_view(), name='sales_profile_details'),


    # AJAX Endpoints
    path('ajax/get-motorcycle-list/', get_motorcycle_list, name='ajax-get-motorcycle-list'),
    path('ajax/get_appointment_times/', get_available_appointment_times_for_date, name='ajax_get_appointment_times'),
    path('ajax/payment-status-check/', ajax_get_payment_status.GetPaymentStatusView.as_view(), name='ajax_sales_payment_status_check'),
]
