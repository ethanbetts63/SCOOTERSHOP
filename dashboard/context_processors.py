# dashboard/context_processors.py

from .models import SiteSettings
from django.conf import settings
from service.models import ServiceType
# Import your HireSettings model
from dashboard.models import HireSettings # Assuming HireSettings is in dashboard.models

def site_settings(request):
    settings_object = None
    service_types_list = []
    hire_settings_object = None 

    try:
        settings_object = SiteSettings.get_settings()
        if settings_object:
            service_types_list = ServiceType.objects.all()
    except Exception:
        # Handle exception for SiteSettings if necessary
        pass # Or log the error

    try:
        hire_settings_object = HireSettings.objects.first()
    except Exception:
        pass 


    return {
        'settings': settings_object, 
        'service_types': service_types_list,
        'hire_settings': hire_settings_object, 
    }