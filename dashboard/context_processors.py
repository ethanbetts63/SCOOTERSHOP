# dashboard/context_processors.py

from .models import SiteSettings
from django.conf import settings
from service.models import ServiceType  

def site_settings(request):
    try:
        settings_object = SiteSettings.get_settings()
        if settings_object:
            service_types_list = ServiceType.objects.all()
    except Exception:
        settings_object = None

    return {'settings': settings_object, 
            'service_types': service_types_list
        }
    