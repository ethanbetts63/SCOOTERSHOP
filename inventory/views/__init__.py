# inventory/views/__init__.py

# Imports for motorcycle detail views
from .motorcycle_detail_view import MotorcycleDetailView

# Imports for motorcycle management views (Create, Update, Delete)
from .motorcycle_create_view import MotorcycleCreateView
from .motorcycle_update_view import MotorcycleUpdateView
from .motorcycle_delete_view import MotorcycleDeleteView

# Import the form handler mixin if it's used directly elsewhere or just for clarity
# from .motorcycle_form_handler_mixin import MotorcycleFormHandlerMixin # Usually not imported here unless needed directly

# Imports for motorcycle list views
from .motorcycle_list_view import MotorcycleListView
from .all_motorcycle_list_view import AllMotorcycleListView
from .new_motorcycle_list_view import NewMotorcycleListView
from .used_motorcycle_list_view import UsedMotorcycleListView

# You might want to list the classes that are intended to be publicly available
__all__ = [
    'MotorcycleDetailView',
    'MotorcycleCreateView',
    'MotorcycleUpdateView',
    'MotorcycleDeleteView',
    'MotorcycleListView',
    'AllMotorcycleListView',
    'NewMotorcycleListView',
    'UsedMotorcycleListView',
]