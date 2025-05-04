# inventory/views/__init__.py

# Imports for motorcycle list views 
from .motorcycle_list import (
    NewMotorcycleListView,
    UsedMotorcycleListView,
    HireMotorcycleListView,
    AllMotorcycleListView,
    new, 
    used, 
    hire, 
)

# Imports for motorcycle detail and management views (formerly in motorcycle_detail.py)
from .motorcycle_detail import (
    MotorcycleDetailView,
    MotorcycleCreateView,
    MotorcycleUpdateView,
    MotorcycleDeleteView,
)
