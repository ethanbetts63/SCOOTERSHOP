from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.urls import reverse # Import reverse for URL lookups
from datetime import datetime, timedelta # Import timedelta for date calculations
from django.utils import timezone # Import timezone for handling aware/naive datetimes

from service.models import ServiceBooking, ServiceType, BlockedServiceDate 


def get_service_bookings_json_ajax(request):
    """
    Function-based view to provide service booking data as a JSON feed for FullCalendar.
    This replaces the class-based ServiceBookingsJsonFeedView.
    """
    # FullCalendar sends start and end parameters in ISO 8601 format
    start_param = request.GET.get('start')
    end_param = request.GET.get('end')

    # Convert ISO 8601 string to timezone-aware datetime objects
    # FullCalendar dates might be UTC, so ensure consistency
    start_date = None
    end_date = None
    if start_param:
        try:
            start_date = timezone.datetime.fromisoformat(start_param.replace('Z', '+00:00'))
            start_date = timezone.localdate(start_date) # Convert to local date if needed, or keep as datetime
        except ValueError:
            pass # Handle invalid date format
    if end_param:
        try:
            end_date = timezone.datetime.fromisoformat(end_param.replace('Z', '+00:00'))
            end_date = timezone.localdate(end_date) # Convert to local date if needed, or keep as datetime
        except ValueError:
            pass # Handle invalid date format

    events = []

    # Filter bookings by dropoff_date within the FullCalendar view range
    bookings_query = ServiceBooking.objects.select_related(
        'service_type',
        'service_profile__user', # Eagerly load user to get full name
        'customer_motorcycle'
    )
    if start_date and end_date:
        # Filter where dropoff_date is between start and end (inclusive for dropoff_date)
        bookings_query = bookings_query.filter(dropoff_date__range=[start_date, end_date - timedelta(days=1)]) # Subtract 1 day for end date to make it inclusive

    bookings = bookings_query.all()
    
    for booking in bookings:
        booking_url = None
        if hasattr(booking, 'pk'):
            try:
                # Use the correct URL name and pass the pk
                booking_url = reverse('service:admin_service_booking_detail', args=[booking.pk])
            except Exception as e:
                # This print will appear in your Django console if URL reversing fails
                print(f"Warning: Could not reverse URL for booking detail (booking PK: {booking.pk}): {e}")

        customer_name = 'N/A'
        if booking.service_profile:
            if booking.service_profile.user and booking.service_profile.user.get_full_name():
                customer_name = booking.service_profile.user.get_full_name()
            elif booking.service_profile.name:
                customer_name = booking.service_profile.name
        
        vehicle_brand = '' # Changed from vehicle_make to vehicle_brand
        vehicle_model = ''
        if booking.customer_motorcycle:
            vehicle_brand = booking.customer_motorcycle.brand
            vehicle_model = booking.customer_motorcycle.model

        # FullCalendar 'end' is exclusive. For all-day events, it should be the day *after* the last day.
        # So, if estimated_pickup_date is the last day, add one day to it.
        event_end_date = booking.estimated_pickup_date if booking.estimated_pickup_date else booking.dropoff_date
        # Add 1 day to make the end date inclusive for display in FullCalendar
        event_end_date_for_fc = (event_end_date + timedelta(days=1)).isoformat()


        events.append({
            'id': booking.pk, 
            'title': f"{customer_name} - {booking.service_type.name if booking.service_type else 'Service'}",
            'start': booking.dropoff_date.isoformat(), 
            'end': event_end_date_for_fc, # Corrected end date for FullCalendar
            'url': booking_url, # Now this should reliably contain the URL
            'extendedProps': {
                'customer_name': customer_name,
                'vehicle_brand': vehicle_brand, # Corrected field name
                'vehicle_model': vehicle_model,
                'service_type': booking.service_type.name if booking.service_type else 'Service',
                'status': booking.booking_status.lower(), 
                'is_blocked': False, 
            }
        })

    # Add blocked dates to the events list
    blocked_dates_query = BlockedServiceDate.objects.all()
    if start_date and end_date:
        # Filter blocked dates that overlap with the FullCalendar view range
        blocked_dates_query = blocked_dates_query.filter(
            start_date__lte=end_date, # Blocked date starts before or on end of view
            end_date__gte=start_date  # Blocked date ends after or on start of view
        )
    blocked_dates = blocked_dates_query.all()

    for blocked_date in blocked_dates:
        # FullCalendar 'end' is exclusive. Add 1 day for all-day blocked events.
        blocked_event_end_date_for_fc = (blocked_date.end_date + timedelta(days=1)).isoformat()

        events.append({
            'id': f"blocked-{blocked_date.pk}", 
            'title': 'Blocked Day',
            'start': blocked_date.start_date.isoformat(),
            'end': blocked_event_end_date_for_fc, # Corrected end date for FullCalendar
            'extendedProps': {
                'is_blocked': True,
                'description': blocked_date.description,
            },
            'display': 'background', 
            'classNames': ['status-blocked'], 
        })

    return JsonResponse(events, safe=False)

