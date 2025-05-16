# SCOOTER_SHOP/dashboard/views/settings_service_types.py

from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

from service.models import ServiceType

@user_passes_test(lambda u: u.is_staff)
def settings_service_types(request):
    service_types = ServiceType.objects.all().order_by('name')
    context = {
        'page_title': 'Service Types Management',
        'service_types': service_types,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/settings_service_types.html', context)