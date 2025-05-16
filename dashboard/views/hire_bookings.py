# hire_bookings.py
import calendar
from datetime import date, timedelta, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime, parse_date

# Import models relevant to Hire Bookings
# Make sure to replace 'hire.models' and 'dashboard.models' with the actual paths
from hire.models import HireBooking # <-- Assume HireBooking model is here
from dashboard.models import BlockedHireDate # <-- Use the BlockedHireDate model

# View for the hire bookings list page (Calendar view)
@user_passes_test(lambda u: u.is_staff)
def hire_bookings_view(request):
    # The actual filtering for the calendar view is done in the JSON feed,
    # so we just need the template here.
    context = {
        'page_title': 'Manage Hire Bookings',
        # No need to fetch all bookings here for the calendar view
    }
    return render(request, 'dashboard/hire_bookings.html', context) # <-- Template for hire bookings calendar

# View for displaying details of a single hire booking
@user_passes_test(lambda u: u.is_staff)
def hire_booking_details_view(request, pk):
    # Fetch a single HireBooking object
    booking = get_object_or_404(HireBooking, pk=pk)

    context = {
        'page_title': f'Hire Booking Details - {booking.booking_reference or booking.id}',
        'booking': booking,
    }
    return render(request, 'dashboard/hire_booking_details.html', context) # <-- Template for hire booking details

# Returns hire bookings and blocked dates as a JSON feed for FullCalendar
@user_passes_test(lambda u: u.is_staff)
def get_hire_bookings_json(request):
    start_param = request.GET.get('start')
    end_param = request.GET.get('end')

    hire_bookings = HireBooking.objects.all()
    blocked_hire_dates = BlockedHireDate.objects.all()

    start_date = None
    end_date = None

    # Filter bookings and blocked dates by the date range FullCalendar requests
    if start_param and end_param:
        try:
            # FullCalendar sends ISO 8601 dates, which can be datetime or just date
            # For bookings with times, parse as datetime. For date ranges, parse as date.
            # The 'start' and 'end' params from FullCalendar are typically datetimes
            # representing the start and end of the *view*.
            start_date_filter = parse_datetime(start_param)
            end_date_filter = parse_datetime(end_param)

            if start_date_filter and end_date_filter:
                # Filter HireBookings that fall within the view range.
                # A booking falls within if its pickup_date is before the end of the view
                # AND its return_date is after the start of the view.
                hire_bookings = hire_bookings.filter(
                    pickup_date__lt=end_date_filter,
                    return_date__gte=start_date_filter.date() # Compare date parts if return_date is just a date field, or adjust as needed
                )
                # Filter blocked dates that overlap with the requested range
                blocked_hire_dates = blocked_hire_dates.filter(
                    start_date__lte=end_date_filter.date(),
                    end_date__gte=start_date_filter.date()
                )


        except (ValueError, TypeError):
            pass # Handle potential parsing errors

    events = []
    # Add hire booking events
    for booking in hire_bookings:
        # Determine the event title - use customer name and potentially vehicle details
        # Adjust this based on what fields are available on your HireBooking model
        customer_display = booking.customer_name or (booking.user.get_full_name() if booking.user else 'Anonymous')
        vehicle_display = booking.vehicle_model.name if hasattr(booking, 'vehicle_model') and booking.vehicle_model else 'Vehicle N/A' # Adjust based on your model

        event_title = f"{customer_display} - {vehicle_display}"

        # Prepare extendedProps for custom rendering in the calendar tile
        extended_props = {
            'customer_name': customer_display,
            'vehicle_display': vehicle_display,
            'status': booking.status, # Assuming HireBooking has a 'status' field
            'booking_reference': booking.booking_reference, # Include booking reference
            'pickup_date': booking.pickup_date.isoformat(),
            'return_date': booking.return_date.isoformat() if booking.return_date else None,
            'booking_id': booking.pk,
        }

        # FullCalendar uses 'start' and 'end' for event duration.
        # For hire bookings, 'start' is the pickup date/time, 'end' is the return date/time.
        # If your model stores dates without time, you might need adjustments.
        event_start = booking.pickup_date.isoformat()
        # FullCalendar's 'end' is exclusive. If the hire ends on a specific date,
        # the 'end' parameter should be the day *after* the return date for it to show
        # on the calendar tile for the return day.
        # Assuming return_date is a DateField:
        event_end = (booking.return_date + timedelta(days=1)).isoformat() if booking.return_date else None
        # If return_date is a DateTimeField:
        # event_end = booking.return_date.isoformat() if booking.return_date else None


        event = {
            'id': booking.pk,
            'title': event_title,
            'start': event_start,
            'end': event_end, # Set the end date/time
            'url': reverse('dashboard:hire_booking_details', args=[booking.pk]), # <-- Update URL name
            'extendedProps': extended_props,
            # Add classes for status styling if needed, similar to service bookings
            'className': f'status-{booking.status}' if hasattr(booking, 'status') else '',
        }
        events.append(event)

    # Add blocked hire date events as regular events
    for blocked_hire_date_range in blocked_hire_dates:
        current_date = blocked_hire_date_range.start_date
        # Ensure end_date is included by adding one day for iteration comparison
        while current_date <= blocked_hire_date_range.end_date:
            blocked_event = {
                'start': current_date.isoformat(),
                'title': 'Blocked Hire Day', # Title for the tile
                'extendedProps': {
                    'is_blocked': True, # Custom property to identify blocked dates
                    'description': blocked_hire_date_range.description, # Include description
                },
                'className': 'blocked-date-tile', # Custom class for styling
                'display': 'block', # Ensure it's treated as a regular event
            }
            events.append(blocked_event)
            current_date += timedelta(days=1)


    return JsonResponse(events, safe=False)

# View for the hire booking search page
@user_passes_test(lambda u: u.is_staff)
def hire_booking_search_view(request):
    query = request.GET.get('q')
    # Default sort can be adjusted based on typical search needs for hire bookings
    sort_by = request.GET.get('sort_by', '-pickup_date') # <-- Changed default sort

    # Get all possible status choices from the HireBooking model
    # Adjust 'STATUS_CHOICES' to match the attribute on your HireBooking model
    booking_statuses = getattr(HireBooking, 'STATUS_CHOICES', [])
    all_status_values = [status[0] for status in booking_statuses]

    # Determine the selected statuses
    if 'status' not in request.GET:
        selected_statuses = all_status_values
    else:
        selected_statuses = request.GET.getlist('status')

    hire_bookings = HireBooking.objects.all()

    # --- Filtering by Status ---
    if selected_statuses:
        # Ensure HireBooking has a 'status' field
        if hasattr(HireBooking, 'status'):
             hire_bookings = hire_bookings.filter(status__in=selected_statuses)
        else:
             # Handle case where status filtering is requested but no status field exists
             messages.warning(request, "Status filtering is not available for Hire Bookings.")
             selected_statuses = [] # Reset selected statuses

    # --- Filtering by Search Query ---
    if query:
        search_filter = Q()

        # Add text field searches relevant to HireBookings
        # Adjust these field names based on your HireBooking model
        search_filter |= Q(customer_name__icontains=query)
        search_filter |= Q(customer_email__icontains=query)
        search_filter |= Q(customer_phone__icontains=query)
        search_filter |= Q(customer_address__icontains=query) # If you store customer address
        search_filter |= Q(booking_reference__icontains=query)

        # Assuming vehicle details are linked or stored on the booking
        # Adjust field names ('vehicle_model__name', 'vehicle__license_plate', etc.)
        # based on how vehicles are related and what fields they have
        if hasattr(HireBooking, 'vehicle_model') and hasattr(HireBooking.vehicle_model, 'name'):
             search_filter |= Q(vehicle_model__name__icontains=query)
        if hasattr(HireBooking, 'vehicle') and hasattr(HireBooking.vehicle, 'license_plate'):
             search_filter |= Q(vehicle__license_plate__icontains=query)
        # Add other relevant fields like notes, etc.
        search_filter |= Q(customer_notes__icontains=query)
        search_filter |= Q(admin_notes__icontains=query) # Assuming an admin_notes field


        hire_bookings = hire_bookings.filter(search_filter)

    # --- Sorting ---
    # Apply sorting based on values from the template.
    # Adjust sortable fields based on HireBooking model and desired options.
    if sort_by == 'id':
        hire_bookings = hire_bookings.order_by('id')
    elif sort_by == '-id':
        hire_bookings = hire_bookings.order_by('-id')
    elif sort_by == 'pickup_date': # <-- Changed from appointment_date
        hire_bookings = hire_bookings.order_by('pickup_date')
    elif sort_by == '-pickup_date': # <-- Changed from appointment_date
        hire_bookings = hire_bookings.order_by('-pickup_date') # Default sort
    elif sort_by == 'return_date': # Added sorting by return date
         if hasattr(HireBooking, 'return_date'):
              hire_bookings = hire_bookings.order_by('return_date')
    elif sort_by == '-return_date': # Added sorting by return date
         if hasattr(HireBooking, 'return_date'):
              hire_bookings = hire_bookings.order_by('-return_date')
    elif sort_by == 'date_created':
        hire_bookings = hire_bookings.order_by('created_at') # Assuming 'created_at' field
    elif sort_by == '-date_created':
        hire_bookings = hire_bookings.order_by('-created_at') # Assuming 'created_at' field
    # No need for an else here, as sort_by has a default value

    context = {
        'page_title': 'Hire Booking Search',
        'bookings': hire_bookings, # Still use 'bookings' in context for template compatibility, but clarify in comments/docs
        'query': query,
        'sort_by': sort_by,
        'selected_statuses': selected_statuses,
        'booking_statuses': booking_statuses, # Pass status choices for the filter dropdown
    }
    return render(request, 'dashboard/hire_booking_search.html', context) # <-- Template for hire booking search