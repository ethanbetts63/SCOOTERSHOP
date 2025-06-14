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
    inventory_management_view,
    inventory_settings_view,
    motorcycle_create_update_view,
    sales_booking_create_update_view,
    sales_booking_details_view,
    sales_bookings_management_view,
    sales_profile_create_update_view,
    sales_profile_details_view,
    sales_profile_management_view,
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
    # Admin Views
    path('admin/settings/', inventory_settings_view.InventorySettingsView.as_view(), name='inventory_settings'),

    # AJAX Endpoints
    path('ajax/get-motorcycle-list/', get_motorcycle_list, name='ajax-get-motorcycle-list'),
    path('ajax/get_appointment_times/', get_available_appointment_times_for_date, name='ajax_get_appointment_times'),
    path('ajax/payment-status-check/', ajax_get_payment_status.GetPaymentStatusView.as_view(), name='ajax_sales_payment_status_check'),
]
