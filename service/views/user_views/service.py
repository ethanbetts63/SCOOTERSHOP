
from django.shortcuts import render, redirect
from django.contrib import messages

                        
from service.models import ServiceType, TempServiceBooking, ServiceSettings
from dashboard.models import SiteSettings 
from service.forms import ServiceDetailsForm
from service.utils import get_service_date_availability

                                                     
def service(request):
    service_settings = ServiceSettings.objects.first()
    settings = SiteSettings.get_settings()
                                                                                                             
                                                                                                  
    if not settings.enable_service_booking:
         messages.error(request, "Service information is currently disabled.")
                                                         
         return redirect('core:index')

                                                              
    try:
        service_types = ServiceType.objects.filter(is_active=True)
    except Exception as e:
        service_types = []                                                        
        messages.warning(request, "Could not load service types.")
    service_form = ServiceDetailsForm()

                                                                                
    temp_service_booking = None
    temp_service_booking_uuid = request.session.get('temp_service_booking_uuid')

    if temp_service_booking_uuid:
        try:
            temp_service_booking = TempServiceBooking.objects.get(session_uuid=temp_service_booking_uuid)
                                                           
            service_form = ServiceDetailsForm(initial={
                'service_type': temp_service_booking.service_type,
                'service_date': temp_service_booking.service_date,                     
            })
        except TempServiceBooking.DoesNotExist:
                                                              
            if 'temp_service_booking_uuid' in request.session:
                del request.session['temp_service_booking_uuid']
            temp_service_booking = None

                                                                           
    min_date_for_flatpickr, disabled_dates_json = get_service_date_availability()


    context = {
        'service_types': service_types,
        'form': service_form,                                  
        'service_settings': service_settings,                                                
        'blocked_service_dates_json': disabled_dates_json,                                         
        'min_service_date_flatpickr': min_date_for_flatpickr.strftime('%Y-%m-%d'),                              
        'temp_service_booking': temp_service_booking,
    }
                           
    return render(request, "service/service.html", context)