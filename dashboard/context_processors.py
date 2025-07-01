                                 

from .models import SiteSettings
from django.conf import settings
from service.models import ServiceType
                                
from dashboard.models import HireSettings                                               

def site_settings(request):
    settings_object = None
    service_types_list = []
    hire_settings_object = None 

    try:
        settings_object = SiteSettings.get_settings()
        if settings_object:
            service_types_list = ServiceType.objects.all()
    except Exception:
                                                        
        pass                   

    try:
        hire_settings_object = HireSettings.objects.first()
    except Exception:
        pass 


    return {
        'settings': settings_object, 
        'service_types': service_types_list,
        'hire_settings': hire_settings_object, 
    }