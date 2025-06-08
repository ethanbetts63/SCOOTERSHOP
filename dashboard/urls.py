# SCOOTER_SHOP/dashboard/urls.py

from django.urls import path
from . import views 
from service.views import *
app_name = 'dashboard'

urlpatterns = [
    # --- Dashboard Index ---
    path('', views.dashboard_index, name='dashboard_index'),

    # --- Hire Booking Management Views ---

    #WHY IS THERE hire-booking and hire-bookings?
    path('hire-bookings/', views.hire_bookings_view, name='hire_bookings'),
    path('hire-bookings/<int:pk>/', views.hire_booking_details_view, name='hire_booking_details'), # Hire booking details view
    path('hire-bookings/search/', views.hire_booking_search_view, name='hire_booking_search'), # Hire booking search view
    path('hire-bookings/json/', views.get_hire_bookings_json, name='get_hire_bookings_json'), # Hire bookings JSON feed
    path('hire-bookings/delete/<int:pk>/', views.delete_hire_booking_view, name='delete_hire_booking'),

    path('settings/hire-booking/', views.settings_hire_booking, name='settings_hire_booking'),
    # --- Other Views (e.g., About Page) ---
    path('edit-about/', views.edit_about_page, name='edit_about_page'),

    # --- Dashboard Settings Views ---
    path('settings/business-info/', views.settings_business_info, name='settings_business_info'),
    path('settings/visibility/', views.settings_visibility, name='settings_visibility'),

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
    # NEW: Driver Profiles URLs
    path('settings/driver-profiles/', views.DriverProfilesSettingsView.as_view(), name='settings_driver_profiles'),
    path('settings/driver-profiles/add/', views.AddEditDriverProfileView.as_view(), name='add_driver_profile'),
    path('settings/driver-profiles/edit/<int:pk>/', views.AddEditDriverProfileView.as_view(), name='edit_driver_profile'),
    path('settings/driver-profiles/delete/<int:pk>/', views.DeleteDriverProfileView.as_view(), name='delete_driver_profile'),
    path('settings/driver-profiles/details/<int:pk>/', views.DriverProfileDetailView.as_view(), name='driver_profile_details')
]
