# SCOOTER_SHOP/dashboard/views/bookings.py

import calendar
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse # Import JsonResponse for the JSON feed

# Import models needed by these views
# Assuming ServiceBooking and ServiceType are in the 'service' app
from service.models import ServiceBooking, ServiceType # Make sure ServiceType is imported if used

# Import forms needed by these views (if any, though booking forms might be elsewhere)
# from dashboard.forms import SomeBookingForm

# Helper function to check if a user is staff (Moved from dashboard.py)
def is_staff_check(user):
    return user.is_staff

# --- Booking List View ---
@user_passes_test(is_staff_check)
def service_bookings_view(request):
    """
    View for the service bookings list page in the admin dashboard.
    Requires staff user.
    """
    # Fetch all service bookings (you might want to filter or order these)
    bookings = ServiceBooking.objects.all().order_by('-appointment_datetime')

    context = {
        'page_title': 'Manage Service Bookings',
        'bookings': bookings, # Pass the bookings list to the template
    }
    # Render the bookings.html template (This template will be updated for FullCalendar)
    return render(request, 'dashboard/service_bookings.html', context)

# --- Service Booking Details View ---
@user_passes_test(is_staff_check)
def service_booking_details_view(request, pk):
    """
    View for displaying details of a single service booking.
    Requires staff user.
    """
    # Get the specific service booking or return a 404 error
    booking = get_object_or_404(ServiceBooking, pk=pk)

    context = {
        'page_title': f'Service Booking Details - {booking.id}', # Use booking ID in title
        'booking': booking, # Pass the specific booking object to the template
    }
    # Render the service_booking_details.html template
    return render(request, 'dashboard/service_booking_details.html', context)

# --- JSON Feed View for FullCalendar (New) ---
@user_passes_test(is_staff_check)
def get_bookings_json(request):
    """
    Returns service bookings as a JSON feed for FullCalendar.
    FullCalendar automatically passes 'start' and 'end' date parameters
    to this view when navigating.
    """
    start_param = request.GET.get('start') # ISO 8601 date/datetime string
    end_param = request.GET.get('end')   # ISO 8601 date/datetime string

    bookings = ServiceBooking.objects.all()

    # Filter bookings by the date range FullCalendar requests
    # FullCalendar sends 'start' and 'end' of the *view*, not just the data range
    # You might need to adjust filtering based on your exact needs
    if start_param and end_param:
        try:
            # FullCalendar sends dates in ISO 8601 format, timezone-aware if applicable
            # Use parse_datetime to handle potential timezone info
            from django.utils.dateparse import parse_datetime
            start_date = parse_datetime(start_param)
            end_date = parse_datetime(end_param)

            if start_date and end_date:
                 # Filter bookings whose appointment_datetime falls within the requested range
                 # Use __gte and __lt for a common range query pattern (end date is exclusive)
                 bookings = bookings.filter(
                     appointment_datetime__gte=start_date,
                     appointment_datetime__lt=end_date # Use < end_date as is standard in many date ranges
                 )

        except (ValueError, TypeError):
             # Handle potential parsing errors, though FullCalendar usually sends correct format
             pass # Or log an error, return an empty list, etc.


    events = []
    for booking in bookings:
        # Prepare the data in FullCalendar's Event Object format
        event = {
            'id': booking.pk, # Use the booking's primary key as the event ID
            'title': f"{booking.customer_name or 'Anonymous'} - {booking.service_type.name}", # Display info
            'start': booking.appointment_datetime.isoformat(), # ISO 8601 format for date and time
            # If your ServiceBooking model had an end time field, you would add it here
            # 'end': booking.end_datetime.isoformat(),
            'url': reverse('dashboard:service_booking_details', args=[booking.pk]), # Link to the detail page
            # You can add other custom properties here, e.g., status, color
            # These custom properties can be accessed in FullCalendar's eventClick or eventRender hooks
            'status': booking.status, # Example: Add booking status
            'color': 'blue' if booking.status == 'confirmed' else ('orange' if booking.status == 'pending' else 'red'), # Example coloring based on status
            'customer_name': booking.customer_name,
            'service_type': booking.service_type.name,
        }
        events.append(event)

    return JsonResponse(events, safe=False) # safe=False is needed when serializing a list