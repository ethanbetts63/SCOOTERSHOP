
from django.shortcuts import render, redirect
from django.contrib import messages

# Updated Model Imports 
from service.models import ServiceType, TempServiceBooking, ServiceSettings
from dashboard.models import SiteSettings 
from service.forms import ServiceDetailsForm
from service.utils import get_service_date_availability

# General Service Information Page (not booking flow)
def service(request):
    service_settings = ServiceSettings.objects.first()
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
        service_types = [] # Ensure service_types is a list even if fetching fails
        messages.warning(request, "Could not load service types.")
    service_form = ServiceDetailsForm()

    # Get TempServiceBooking from session for pre-populating service Step 1 form
    temp_service_booking = None
    temp_service_booking_uuid = request.session.get('temp_service_booking_uuid')

    if temp_service_booking_uuid:
        try:
            temp_service_booking = TempServiceBooking.objects.get(session_uuid=temp_service_booking_uuid)
            # If found, pre-populate the form with its data
            service_form = ServiceDetailsForm(initial={
                'service_type': temp_service_booking.service_type,
                'service_date': temp_service_booking.service_date, # Updated field name
            })
        except TempServiceBooking.DoesNotExist:
            # If temp booking doesn't exist, clear session key
            if 'temp_service_booking_uuid' in request.session:
                del request.session['temp_service_booking_uuid']
            temp_service_booking = None

    # Call the new utility function to get min_date and disabled_dates_json
    min_date_for_flatpickr, disabled_dates_json = get_service_date_availability()


    context = {
        'service_types': service_types,
        'form': service_form, # The ServiceDetailsForm instance
        'service_settings': service_settings, # Pass service settings for the service include
        'blocked_service_dates_json': disabled_dates_json, # Blocked dates for service from utility
        'min_service_date_flatpickr': min_date_for_flatpickr.strftime('%Y-%m-%d'), # Pass min date for Flatpickr
        'temp_service_booking': temp_service_booking,
    }
    # Updated template path
    return render(request, "service/service.html", context)