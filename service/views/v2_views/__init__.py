from . import user_views
from . import admin_views

# Define what gets imported when someone does 'from service.views.v2_views import *'
__all__ = ['user_views', 'admin_views']
