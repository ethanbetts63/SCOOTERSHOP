from django.urls import path
from . import views 
from service.views import *
app_name = 'dashboard'

from .views.featured_motorcycle_management import FeaturedMotorcycleManagementView
from .views.featured_motorcycle_create import FeaturedMotorcycleCreateView

urlpatterns = [                            
    path('', views.dashboard_index, name='dashboard_index'),               
    path('edit-about/', views.edit_about_page, name='edit_about_page'),                              
    path('settings/business-info/', views.settings_business_info, name='settings_business_info'),
    path('settings/visibility/', views.settings_visibility, name='settings_visibility'),
    path('featured-motorcycles/', FeaturedMotorcycleManagementView.as_view(), name='featured_motorcycles'),
    path('featured-motorcycles/add/', FeaturedMotorcycleCreateView.as_view(), name='add_featured_motorcycle'),
]
