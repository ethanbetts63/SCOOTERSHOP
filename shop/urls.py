# SCOOTER_SHOP/shop/urls.py

from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # --- Main Site Pages ---
    path('', views.index, name='index'),
    path('service', views.service, name='service'),

    # --- Information Pages ---
    path('about', views.about, name='about'),
    path('contact', views.contact, name='contact'),
    path('privacy', views.privacy, name='privacy'),
    path('returns', views.returns, name='returns'),
    path('security', views.security, name='security'),
    path('terms', views.terms, name='terms'),

    # --- Authentication Views ---
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),

    # --- Motorcycle List Views ---
    path('motorcycles/', views.NewMotorcycleListView.as_view(), name='motorcycle-list'),
    path('new/', views.new, name='new'),
    path('used/', views.used, name='used'),
    path('hire/', views.hire, name='hire'),

    # --- Motorcycle Detail/Management Views ---
    path('motorcycles/<int:pk>/', views.MotorcycleDetailView.as_view(), name='motorcycle-detail'),
    path('motorcycles/create/', views.MotorcycleCreateView.as_view(), name='motorcycle-create'),
    path('motorcycles/<int:pk>/update/', views.MotorcycleUpdateView.as_view(), name='motorcycle-update'),
    path('motorcycles/<int:pk>/delete/', views.MotorcycleDeleteView.as_view(), name='motorcycle-delete'),

    # --- Service Booking Views (Split for Auth/Anonymous) ---
    path('book/start/', views.service_booking_start, name='service_booking_start'),

    # Authenticated Flow
    path('book/auth/step1/', views.service_booking_step1_authenticated, name='service_booking_step1_authenticated'),
    path('book/auth/step2/', views.service_booking_step2_authenticated, name='service_booking_step2_authenticated'),
    path('book/auth/step3/', views.service_booking_step3_authenticated, name='service_booking_step3_authenticated'),

    # Anonymous Flow
    path('book/anon/step1/', views.service_booking_step1_anonymous, name='service_booking_step1_anonymous'),
    path('book/anon/step2/', views.service_booking_step2_anonymous, name='service_booking_step2_anonymous'),
    path('book/anon/step3/', views.service_booking_step3_anonymous, name='service_booking_step3_anonymous'),

    path('book/confirmed/', views.service_booking_not_yet_confirmed_view, name='service_booking_not_yet_confirmed'),


    # --- Dashboard Views ---
    path('dashboard/', views.dashboard_index, name='dashboard_index'),
    path('dashboard/edit-about/', views.edit_about_page, name='edit_about_page'),

    # --- Dashboard Settings Views ---
    path('dashboard/settings/business-info/', views.settings_business_info, name='settings_business_info'),
    path('dashboard/settings/visibility/', views.settings_visibility, name='settings_visibility'),
    path('dashboard/settings/service-booking/', views.settings_service_booking, name='settings_service_booking'),
    path('dashboard/settings/hire-booking/', views.settings_hire_booking, name='settings_hire_booking'),
    path('dashboard/settings/miscellaneous/', views.settings_miscellaneous, name='settings_miscellaneous'),

    # --- Dashboard Service Type Management Views ---
    path('dashboard/settings/service-types/', views.settings_service_types, name='settings_service_types'),
    path('dashboard/settings/service-types/add/', views.add_service_type, name='add_service_type'),
    path('dashboard/settings/service-types/edit/<int:pk>/', views.edit_service_type, name='edit_service_type'),
    path('dashboard/settings/service-types/delete/<int:pk>/', views.delete_service_type, name='delete_service_type'),
]