# SCOOTER_SHOP/dashboard/urls.py

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='dashboard_index'),

    # Settings URLs
    path('settings/business-info/', views.settings_business_info, name='settings_business_info'),
    path('settings/hire-booking/', views.settings_hire_booking, name='settings_hire_booking'),
    path('settings/service-booking/', views.settings_service_booking, name='settings_service_booking'),
    path('settings/service-types/', views.settings_service_types, name='settings_service_types'),
    path('settings/visibility/', views.settings_visibility, name='settings_visibility'),
    path('settings/about-page/', views.edit_about_page, name='edit_about_page'),
    path('settings/service-brands/', views.service_brands_management, name='service_brands_management'),

    # Service Type Actions
    path('service-types/delete/<int:pk>/', views.delete_service_type, name='delete_service_type'),
    path('service-types/edit/<int:pk>/', views.edit_service_type, name='edit_service_type'),
    path('service-types/add/', views.add_service_type, name='add_service_type'),
    path('service-types/toggle-active/<int:pk>/', views.toggle_service_type_active_status, name='toggle_service_type_active_status'),
    path('service-brands/delete/<int:pk>/', views.delete_service_brand, name='delete_service_brand'),


    # New URLs for Blocked Dates
    path('settings/blocked-service-dates/', views.blocked_service_dates_management, name='blocked_service_dates_management'),
    path('settings/blocked-service-dates/delete/<int:pk>/', views.delete_blocked_service_date, name='delete_blocked_service_date'),
    path('settings/blocked-hire-dates/', views.blocked_hire_dates_management, name='blocked_hire_dates_management'),
    path('settings/blocked-hire-dates/delete/<int:pk>/', views.delete_blocked_hire_date, name='delete_blocked_hire_date'),
]
