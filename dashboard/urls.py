                                

from django.urls import path
from . import views 
from service.views import *
app_name = 'dashboard'

urlpatterns = [
                             
    path('', views.dashboard_index, name='dashboard_index'),
                     
    path('edit-about/', views.edit_about_page, name='edit_about_page'),

                                      
    path('settings/business-info/', views.settings_business_info, name='settings_business_info'),
    path('settings/visibility/', views.settings_visibility, name='settings_visibility'),
]
