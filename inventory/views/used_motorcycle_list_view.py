# inventory/views/used_motorcycle_list_view.py

from .motorcycle_list_view import MotorcycleListView 

class UsedMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/used.html'
    condition_name = 'used'
    url_name = 'inventory:used'
