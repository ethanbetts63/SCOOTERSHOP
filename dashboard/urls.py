# This is the updated version of your dashboard/urls.py
from django.urls import path
from dashboard.views import (
    DashboardIndexView, 
    SettingsBusinessInfoView, 
    SettingsVisibilityView,
    ClearNotificationsView, 
    ReviewsManagementView, 
    ReviewCreateUpdateView, 
    ReviewDetailsView, 
    ReviewDeleteView

)

app_name = 'dashboard'

urlpatterns = [                            
    path('', DashboardIndexView.as_view(), name='dashboard_index'),
    path('notifications/clear/', ClearNotificationsView.as_view(), name='clear_notifications'),
    path('settings/business-info/', SettingsBusinessInfoView.as_view(), name='settings_business_info'),
    path('settings/visibility/', SettingsVisibilityView.as_view(), name='settings_visibility'),

    # Review Management URLs
    path('reviews/', ReviewsManagementView.as_view(), name='reviews_management'),
    path('reviews/create/', ReviewCreateUpdateView.as_view(), name='review_create'),
    path('reviews/<int:pk>/', ReviewDetailsView.as_view(), name='review_details'),
    path('reviews/<int:pk>/update/', ReviewCreateUpdateView.as_view(), name='review_update'),
    path('reviews/<int:pk>/delete/', ReviewDeleteView.as_view(), name='review_delete'),
]