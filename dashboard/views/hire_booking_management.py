# hire_booking_management.py
import calendar
from datetime import date, timedelta, datetime
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime, parse_date

from hire.models import HireBooking
from dashboard.models import BlockedHireDate

@user_passes_test(lambda u: u.is_staff)
def hire_bookings_view(request):
    """
    Renders the main hire bookings calendar page for staff users.
    """
    context = {
        'page_title': 'Manage Hire Bookings',
    }
    return render(request, 'dashboard/hire_bookings.html', context)

@user_passes_test(lambda u: u.is_staff)
def get_hire_bookings_json(request):
    """
    Returns a JSON feed of hire bookings and blocked dates for FullCalendar.
    Filters bookings and blocked dates based on the 'start' and 'end' parameters
    provided by FullCalendar.
    """
    start_param = request.GET.get('start')
    end_param = request.GET.get('end')

    hire_bookings = HireBooking.objects.all()
    blocked_hire_dates = BlockedHireDate.objects.all()

    if start_param and end_param:
        try:
            start_date_filter = parse_datetime(start_param)
            end_date_filter = parse_datetime(end_param)

            if start_date_filter and end_date_filter:
                hire_bookings = hire_bookings.filter(
                    pickup_date__lt=end_date_filter,
                    return_date__gte=start_date_filter.date()
                )
                blocked_hire_dates = blocked_hire_dates.filter(
                    start_date__lte=end_date_filter.date(),
                    end_date__gte=start_date_filter.date()
                )

        except (ValueError, TypeError):
            # Error during date parsing, continue without filtering
            pass

    events = []

    for booking in hire_bookings:
        customer_display = 'Anonymous'
        if booking.driver_profile:
            if booking.driver_profile.user:
                customer_display = booking.driver_profile.user.get_full_name() or booking.driver_profile.name
            else:
                customer_display = booking.driver_profile.name or 'Anonymous'
        
        vehicle_display = str(booking.motorcycle) if booking.motorcycle else 'Vehicle N/A' 

        event_title = f"{customer_display} - {vehicle_display}"

        extended_props = {
            'customer_name': customer_display,
            'vehicle_display': vehicle_display,
            'status': booking.status,
            'booking_reference': booking.booking_reference,
            'pickup_date': booking.pickup_date.isoformat(),
            'return_date': booking.return_date.isoformat() if booking.return_date else None,
            'booking_id': booking.pk,
        }

        event_start = booking.pickup_date.isoformat()
        event_end = (booking.return_date + timedelta(days=1)).isoformat() if booking.return_date else None
        
        event = {
            'id': booking.pk,
            'title': event_title,
            'start': event_start,
            'end': event_end,
            'url': reverse('dashboard:hire_booking_details', args=[booking.pk]),
            'extendedProps': extended_props,
            'className': f'status-{booking.status}' if hasattr(booking, 'status') else '',
        }
        events.append(event)

    for blocked_hire_date_range in blocked_hire_dates:
        current_date = blocked_hire_date_range.start_date
        while current_date <= blocked_hire_date_range.end_date:
            blocked_event = {
                'start': current_date.isoformat(),
                'title': 'Blocked Hire Day',
                'extendedProps': {
                    'is_blocked': True,
                    'description': blocked_hire_date_range.description,
                },
                'className': 'blocked-date-tile',
                'display': 'block',
            }
            events.append(blocked_event)
            current_date += timedelta(days=1)

    return JsonResponse(events, safe=False)
