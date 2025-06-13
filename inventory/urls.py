# SCOOTER_SHOP/inventory/urls.py

from django.urls import path

from .views.user_views import (
    motorcycle_list_view, 
    step1_details_appointment_and_motorcycle_view, 
    step2_payment_view, 
    step3_confirmation_view, 
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
)

app_name = 'inventory'

urlpatterns = [
    # Motorcycle List View
    path('motorcycles/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'all'}, name='all'),
    path('motorcycles/new/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'new'}, name='new'),
    path('motorcycles/used/', motorcycle_list_view.MotorcycleListView.as_view(), {'condition_slug': 'used'}, name='used'),

    # Motorcycle Details View for Users
    path('motorcycles/<int:pk>/', user_motorcycle_details_view.UserMotorcycleDetailsView.as_view(), name='motorcycle-detail'),

    # Admin Views
    path('admin/settings/', inventory_settings_view.InventorySettingsView.as_view(), name='inventory_settings'),
    
    # AJAX Endpoints
    path('ajax/get-motorcycle-list/', get_motorcycle_list, name='ajax-get-motorcycle-list'),

]