from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.urls import reverse # Import reverse for URL lookups

from service.models import ServiceBooking, ServiceType, BlockedServiceDate # Ensure your model path is correct


def get_service_bookings_json_ajax(request):
    """
    Function-based view to provide service booking data as a JSON feed for FullCalendar.
    This replaces the class-based ServiceBookingsJsonFeedView.
    """
    bookings = ServiceBooking.objects.select_related(
        'service_type',
        'service_profile',
        'customer_motorcycle'
    ).all()
    
    events = []
    for booking in bookings:
        booking_url = None
        if hasattr(booking, 'pk'):
            try:
                booking_url = reverse('service:booking_detail', args=[booking.pk])
            except Exception as e:
                # Handle case where 'service:booking_detail' might not be defined
                print(f"Warning: Could not reverse URL for booking detail (booking PK: {booking.pk}): {e}")

        # Get customer and vehicle details safely
        customer_name = booking.service_profile.name if booking.service_profile else 'Unknown Customer'
        
        vehicle_make = ''
        vehicle_model = ''
        if booking.customer_motorcycle:
            vehicle_make = booking.customer_motorcycle.brand
            vehicle_model = booking.customer_motorcycle.model

        events.append({
            'id': booking.pk, # Unique ID for the event
            'title': f"{customer_name} - {booking.service_type.name if booking.service_type else 'Service'}",
            'start': booking.dropoff_date.isoformat(), # FullCalendar expects ISO 8601 format
            'end': booking.estimated_pickup_date.isoformat() if booking.estimated_pickup_date else booking.dropoff_date.isoformat(),
            'url': booking_url, # Link to the booking detail page
            'extendedProps': {
                'customer_name': customer_name,
                'vehicle_make': vehicle_make,
                'vehicle_model': vehicle_model,
                'service_type': booking.service_type.name if booking.service_type else 'Service',
                'status': booking.booking_status.lower(), # Ensure status is lowercase for CSS classes
                'is_blocked': False, # This event is a real booking, not a blocked date
            }
        })

    # Add blocked dates to the events list
    # Assuming you have a BlockedServiceDate model with 'date' and 'reason' fields
    blocked_dates = BlockedServiceDate.objects.all()
    for blocked_date in blocked_dates:
        events.append({
            'id': f"blocked-{blocked_date.pk}", # Unique ID for blocked dates
            'title': 'Blocked Day',
            'start': blocked_date.date.isoformat(),
            'end': blocked_date.date.isoformat(), # Blocked dates are usually single-day events
            'extendedProps': {
                'is_blocked': True,
                'description': blocked_date.reason,
            },
            'display': 'background', # Render as a background event
            'classNames': ['status-blocked'], # Apply specific styling
        })

    return JsonResponse(events, safe=False)
