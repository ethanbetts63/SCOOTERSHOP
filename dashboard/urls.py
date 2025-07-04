from django.urls import path
from dashboard.views import (
    DashboardIndexView, 
    SettingsBusinessInfoView, 
    SettingsVisibilityView
)

app_name = 'dashboard'

urlpatterns = [                            
    path('', DashboardIndexView.as_view(), name='dashboard_index'),               
    path('settings/business-info/', SettingsBusinessInfoView.as_view(), name='settings_business_info'),
    path('settings/visibility/', SettingsVisibilityView.as_view(), name='settings_visibility'),
]
