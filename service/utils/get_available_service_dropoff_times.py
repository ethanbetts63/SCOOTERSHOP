import datetime
from django.utils import timezone
from service.models import ServiceSettings, ServiceBooking

def get_available_dropoff_times(selected_date):
    """
    Calculates and returns a list of available drop-off times for a given date.
    This function considers:
    1. The global drop_off_start_time and drop_off_end_time from ServiceSettings,
       unless allow_after_hours_dropoff is enabled.
    2. The drop_off_spacing_mins from ServiceSettings to create intervals.
    3. Existing bookings on the selected_date and disables slots around them
       based on the drop_off_spacing_mins.
    4. If the selected_date is today, it restricts available times to be
       on or before latest_same_day_dropoff_time from ServiceSettings,
       unless allow_after_hours_dropoff is enabled.

    Args:
        selected_date (datetime.date): The date for which to find available times.

    Returns:
        list: A list of strings, each representing an available time slot in "HH:MM" format.
              Returns an empty list if no settings are found or no slots are available.
    """
    service_settings = ServiceSettings.objects.first()
    if not service_settings:
                                                                  
        return []

    allow_after_hours_dropoff = service_settings.allow_after_hours_dropoff

                                                           
    now = timezone.now()

                                                                                         
    if allow_after_hours_dropoff:
                                                                                            
        start_time_obj = datetime.time(0, 0)         
        end_time_obj = datetime.time(23, 59)        
    else:
                                                   
        start_time_obj = service_settings.drop_off_start_time
        end_time_obj = service_settings.drop_off_end_time

                                                       
        today_local = timezone.localdate(now)                                                            

                                                                             
                                          
        if selected_date <= today_local:
                                                                              
            if service_settings.latest_same_day_dropoff_time < end_time_obj:
                end_time_obj = service_settings.latest_same_day_dropoff_time

    spacing_minutes = service_settings.drop_off_spacing_mins

                                                        
    potential_slots = []

                                                                                          
                                                                                               
    current_slot_datetime = timezone.make_aware(
        datetime.datetime.combine(selected_date, start_time_obj),
        timezone=timezone.get_current_timezone()                                   
    )
    end_slot_datetime = timezone.make_aware(
        datetime.datetime.combine(selected_date, end_time_obj),
        timezone=timezone.get_current_timezone()                                   
    )

                                                                          
    while current_slot_datetime <= end_slot_datetime:
                                                                                             
                                                                                   
        if not allow_after_hours_dropoff and selected_date <= today_local and\
           current_slot_datetime < now:                          
            current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)
            continue                  

        potential_slots.append(current_slot_datetime.strftime('%H:%M'))
        current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)

    available_slots_set = set(potential_slots)                                             

                                                      
                                                         
    bookings = ServiceBooking.objects.filter(dropoff_date=selected_date, dropoff_time__isnull=False)

                                                                           
    for booking in bookings:
                                                                        
                                                                                 
        booked_time_dt = timezone.make_aware(
            datetime.datetime.combine(selected_date, booking.dropoff_time),
            timezone=timezone.get_current_timezone()                                   
        )
        block_start_datetime = booked_time_dt - datetime.timedelta(minutes=spacing_minutes)
        block_end_datetime = booked_time_dt + datetime.timedelta(minutes=spacing_minutes)

                                                                                        
        slots_to_remove = set()
        for slot_str in available_slots_set:
                                                         
            slot_time = datetime.datetime.strptime(slot_str, '%H:%M').time()
                                                              
            slot_datetime = timezone.make_aware(
                datetime.datetime.combine(selected_date, slot_time),
                timezone=timezone.get_current_timezone()                                   
            )

            if block_start_datetime <= slot_datetime <= block_end_datetime:
                slots_to_remove.add(slot_str)
        
        available_slots_set -= slots_to_remove                                      
        
    final_available_slots = []
                                                                                                
                                                           
    for slot_str in potential_slots:
        if slot_str in available_slots_set:
            final_available_slots.append(slot_str)

    return final_available_slots