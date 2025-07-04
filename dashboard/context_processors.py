from .models import VisibilitySettings, BusinessInfo
from django.conf import settings
from service.models import ServiceType
                                
def site_settings(request):
    visibility_settings = None
    business_info_settings = None
    service_types_list = []

    try:
        visibility_settings = VisibilitySettings.get_settings()
        business_info_settings = BusinessInfo.get_settings()
        service_types_list = ServiceType.objects.all()
    except Exception:                                              
        pass                   

    return {
        'visibility_settings': visibility_settings,
        'business_info_settings': business_info_settings,
        'service_types': service_types_list,
    }