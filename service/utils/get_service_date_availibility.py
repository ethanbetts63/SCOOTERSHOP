import datetime
from django.utils import timezone
from django.conf import settings
import json

from service.models import ServiceSettings, BlockedServiceDate
                                                             
                                                                                 
from service.models import ServiceBooking                                                                    

def get_service_date_availability():
    
    service_settings = ServiceSettings.objects.first()
    
                                            
    now_in_perth = timezone.localtime(timezone.now()).date()

    min_date = now_in_perth
    if service_settings and service_settings.booking_advance_notice is not None:
        min_date = now_in_perth + datetime.timedelta(days=service_settings.booking_advance_notice)

                                                         
    disabled_dates_for_flatpickr = []

                               
    blocked_dates_queryset = BlockedServiceDate.objects.all()
    for blocked_date in blocked_dates_queryset:
        disabled_dates_for_flatpickr.append({
            'from': str(blocked_date.start_date),
            'to': str(blocked_date.end_date)
        })

                                                               
    day_names_map = {
        0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
        4: 'Fri', 5: 'Sat', 6: 'Sun'
    }
    
                                                                  
                                                               
                                                                       
    start_checking_date = min_date
    for i in range(366):                                                 
        current_check_date = start_checking_date + datetime.timedelta(days=i)
        current_day_abbr = day_names_map.get(current_check_date.weekday())
        
                                             
        if service_settings and service_settings.booking_open_days:
            open_days_list = [d.strip() for d in service_settings.booking_open_days.split(',')]
            if current_day_abbr not in open_days_list:
                disabled_dates_for_flatpickr.append(str(current_check_date))
                continue                                               

                                                                           
                                                                      
        if service_settings and service_settings.max_visible_slots_per_day is not None:
            booked_slots_count = ServiceBooking.objects.filter(
                dropoff_date=current_check_date,
                booking_status__in=['pending', 'confirmed', 'in_progress']                                                  
            ).count()

            if booked_slots_count >= service_settings.max_visible_slots_per_day:
                disabled_dates_for_flatpickr.append(str(current_check_date))

                                                            
                                                                     

                                                        
    disabled_dates_json = json.dumps(disabled_dates_for_flatpickr)

    return min_date, disabled_dates_json

