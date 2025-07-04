from django.urls import path
from dashboard.views import (
    DashboardIndexView, 
    SettingsBusinessInfoView, 
    SettingsVisibilityView

)
app_name = 'dashboard'

urlpatterns = [                            
    path('', DashboardIndexView, name='dashboard_index'),               
    path('settings/business-info/', SettingsBusinessInfoView, name='settings_business_info'),
    path('settings/visibility/', SettingsVisibilityView, name='settings_visibility'),
]
