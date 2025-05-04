# SCOOTER_SHOP/inventory/urls.py

from django.urls import path
# Import the necessary views from your inventory app
from .views import (
    NewMotorcycleListView, used, hire, AllMotorcycleListView, MotorcycleDetailView,
    MotorcycleCreateView, MotorcycleUpdateView, MotorcycleDeleteView
) 


app_name = 'inventory' 

urlpatterns = [
    # --- Motorcycle List Views ---
    path('', AllMotorcycleListView.as_view(), name='motorcycle-list'), # e.g., /inventory/
    path('new/', NewMotorcycleListView.as_view(), {'condition': 'new'}, name='new'), # Example for filtering
    path('used/', used, name='used'), # Assuming 'used' view is a simple function
    path('hire/', hire, name='hire'), # Assuming 'hire' view is a simple function

    # --- Motorcycle Detail/Management Views ---
    path('<int:pk>/', MotorcycleDetailView.as_view(), name='motorcycle-detail'), # e.g., /inventory/1/
    path('create/', MotorcycleCreateView.as_view(), name='motorcycle-create'),
    path('<int:pk>/update/', MotorcycleUpdateView.as_view(), name='motorcycle-update'),
    path('<int:pk>/delete/', MotorcycleDeleteView.as_view(), name='motorcycle-delete'),
]