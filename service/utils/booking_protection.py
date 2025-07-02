import datetime
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

def set_recent_booking_flag(request):
    
    request.session['last_booking_successful_timestamp'] = timezone.now().isoformat()

def check_and_manage_recent_booking_flag(request):
    
    last_booking_timestamp_str = request.session.get('last_booking_successful_timestamp')

    if last_booking_timestamp_str:
        try:
            last_booking_time = timezone.datetime.fromisoformat(last_booking_timestamp_str)
            cooling_off_period = datetime.timedelta(minutes=2)

            if timezone.now() - last_booking_time < cooling_off_period:
                messages.warning(request, "You recently completed a booking. If you wish to make another, please ensure your previous booking was processed successfully or wait a few moments.")
                return redirect(reverse('service:service'))
            else:
                del request.session['last_booking_successful_timestamp']
        except (ValueError, TypeError):
            request.session.pop('last_booking_successful_timestamp', None)
    return None 
