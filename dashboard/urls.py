# SCOOTER_SHOP/dashboard/urls.py

from django.urls import path
from . import views # This imports all views exposed in __init__.py

app_name = 'dashboard' # Set the app name for namespacing

urlpatterns = [
    # --- Dashboard Index ---
    path('', views.dashboard_index, name='dashboard_index'),

    # --- Service Booking Management Views ---
    # These views are imported via views/__init__.py from views/service_bookings.py
    path('service-bookings/', views.service_bookings_view, name='service_bookings'),
    path('service-bookings/<int:pk>/', views.service_booking_details_view, name='service_booking_details'),
    path('service-bookings/search/', views.service_booking_search_view, name='service_booking_search'),
    path('service-bookings/json/', views.get_service_bookings_json, name='get_service_bookings_json'), # Renamed JSON feed URL

    # --- Hire Booking Management Views ---
    # These views will be imported via views/__init__.py from views/hire_bookings.py
    path('hire-bookings/', views.hire_bookings_view, name='hire_bookings'), # Hire bookings calendar view
    path('hire-bookings/<int:pk>/', views.hire_booking_details_view, name='hire_booking_details'), # Hire booking details view
    path('hire-bookings/search/', views.hire_booking_search_view, name='hire_booking_search'), # Hire booking search view
    path('hire-bookings/json/', views.get_hire_bookings_json, name='get_hire_bookings_json'), # Hire bookings JSON feed

    # --- Other Views (e.g., About Page) ---
    path('edit-about/', views.edit_about_page, name='edit_about_page'),

    # --- Dashboard Settings Views ---
    path('settings/business-info/', views.settings_business_info, name='settings_business_info'),
    path('settings/visibility/', views.settings_visibility, name='settings_visibility'),
    path('settings/service-booking/', views.settings_service_booking, name='settings_service_booking'),
    path('settings/hire-booking/', views.settings_hire_booking, name='settings_hire_booking'),


    # --- Dashboard Service Brand Management Views ---
    path('settings/service-brands/', views.service_brands_management, name='service_brands_management'),
    path('settings/service-brands/delete/<int:pk>/', views.delete_service_brand, name='delete_service_brand'),

    # --- Dashboard Service Type Management Views ---
    path('settings/service-types/', views.settings_service_types, name='settings_service_types'),
    path('settings/service-types/add/', views.add_service_type, name='add_service_type'),
    path('settings/service-types/edit/<int:pk>/', views.edit_service_type, name='edit_service_type'),
    path('settings/service-types/delete/<int:pk>/', views.delete_service_type, name='delete_service_type'),
    path('settings/service-types/toggle-active/<int:pk>/', views.toggle_service_type_active_status, name='toggle_service_type_active_status'),

    # --- Blocked Dates Management Views ---
    path('settings/blocked-service-dates/', views.blocked_service_dates_management, name='blocked_service_dates_management'),
    path('settings/blocked-service-dates/delete/<int:pk>/', views.delete_blocked_service_date, name='delete_blocked_service_date'),
    path('settings/blocked-hire-dates/', views.blocked_hire_dates_management, name='blocked_hire_dates_management'),
    path('settings/blocked-hire-dates/delete/<int:pk>/', views.delete_blocked_hire_date, name='delete_blocked_hire_date'),

        # --- Dashboard Hire Add-On Management Views ---
    path('settings/hire-addons/', views.settings_hire_addons, name='settings_hire_addons'),
    path('settings/hire-addons/add/', views.AddEditAddOnView.as_view(), name='add_hire_addon'),
    path('settings/hire-addons/edit/<int:pk>/', views.AddEditAddOnView.as_view(), name='edit_hire_addon'),
    path('settings/hire-addons/delete/<int:pk>/', views.delete_addon, name='delete_hire_addon'),

    # Hire Packages URLs
    path('settings/hire-packages/', views.HirePackagesSettingsView.as_view(), name='settings_hire_packages'),
    path('settings/hire-packages/add/', views.AddEditPackageView.as_view(), name='add_hire_package'),
    path('settings/hire-packages/edit/<int:pk>/', views.AddEditPackageView.as_view(), name='edit_hire_package'),
    path('settings/hire-packages/delete/<int:pk>/', views.DeletePackageView.as_view(), name='delete_hire_package'),
]