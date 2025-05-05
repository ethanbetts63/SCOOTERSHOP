
from django.shortcuts import render, redirect
from django.contrib import messages

# Updated Model Imports 
from service.models import ServiceType
from dashboard.models import SiteSettings 


# General Service Information Page (not booking flow)
def service(request):
    settings = SiteSettings.get_settings()
    # Check if the general service info page is enabled (assuming a new setting or using the booking setting)
    # Let's use the enable_service_booking setting for now, adjust if a dedicated setting is added
    if not settings.enable_service_booking:
         messages.error(request, "Service information is currently disabled.")
         # Updated redirect URL to use the core namespace
         return redirect('core:index')

    # Get all active service types to display on the info page
    try:
        service_types = ServiceType.objects.filter(is_active=True)
    except Exception as e:
        print(f"Error fetching service types for service info page: {e}")
        service_types = [] # Ensure service_types is a list even if fetching fails
        messages.warning(request, "Could not load service types.")


    context = {
        'service_types': service_types
    }
    # Updated template path
    return render(request, "service:service", context)