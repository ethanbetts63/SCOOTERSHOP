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

# from .ajax import (

# )


app_name = 'inventory'

urlpatterns = [

]