# SCOOTER_SHOP/inventory/urls.py

from django.urls import path

# Import the necessary views from your inventory app
from .views import (
    NewMotorcycleListView, UsedMotorcycleListView, 
    AllMotorcycleListView, MotorcycleDetailView,
    MotorcycleCreateView, MotorcycleUpdateView, MotorcycleDeleteView
)


app_name = 'inventory'

urlpatterns = [
    # --- Motorcycle List Views ---
    path('', AllMotorcycleListView.as_view(), name='motorcycle-list'),
    path('new/', NewMotorcycleListView.as_view(), {'condition_name': 'new'}, name='new'), 
    path('used/', UsedMotorcycleListView.as_view(), {'condition_name': 'used'}, name='used'), 

    # --- Motorcycle Detail/Management Views ---
    path('<int:pk>/', MotorcycleDetailView.as_view(), name='motorcycle-detail'),
    path('create/', MotorcycleCreateView.as_view(), name='motorcycle-create'),
    path('<int:pk>/update/', MotorcycleUpdateView.as_view(), name='motorcycle-update'),
    path('<int:pk>/delete/', MotorcycleDeleteView.as_view(), name='motorcycle-delete'),
]