from .models import SiteSettings
from django.conf import settings
from service.models import ServiceType


def site_settings(request):
    settings_object = None
    service_types_list = []

    try:
        settings_object = SiteSettings.get_settings()
        if settings_object:
            service_types_list = ServiceType.objects.all()
    except Exception:
        pass

    return {
        "settings": settings_object,
        "service_types": service_types_list,
        "SITE_DOMAIN": settings.SITE_DOMAIN,
        "SITE_SCHEME": settings.SITE_SCHEME,
    }
