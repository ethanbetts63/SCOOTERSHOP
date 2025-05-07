# bookings.py
import calendar
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse

from service.models import ServiceBooking, ServiceType # Ensure your model path is correct

# Helper function to check if a user is staff
def is_staff_check(user):
    return user.is_staff

# View for the service bookings list page
@user_passes_test(is_staff_check)
def service_bookings_view(request):
    bookings = ServiceBooking.objects.all().order_by('-appointment_datetime')

    context = {
        'page_title': 'Manage Service Bookings',
        'bookings': bookings,
    }
    return render(request, 'dashboard/service_bookings.html', context) # Make sure this template name is correct

# View for displaying details of a single service booking
@user_passes_test(is_staff_check)
def service_booking_details_view(request, pk):
    booking = get_object_or_404(ServiceBooking, pk=pk)

    context = {
        'page_title': f'Service Booking Details - {booking.id}',
        'booking': booking,
    }
    return render(request, 'dashboard/service_booking_details.html', context) # Make sure this template name is correct

# Returns service bookings as a JSON feed for FullCalendar
@user_passes_test(is_staff_check)
def get_bookings_json(request):
    start_param = request.GET.get('start')
    end_param = request.GET.get('end')

    bookings = ServiceBooking.objects.all()

    # Filter bookings by the date range FullCalendar requests
    if start_param and end_param:
        try:
            from django.utils.dateparse import parse_datetime
            start_date = parse_datetime(start_param)
            end_date = parse_datetime(end_param)

            if start_date and end_date:
                 bookings = bookings.filter(
                     appointment_datetime__gte=start_date,
                     appointment_datetime__lt=end_date
                 )

        except (ValueError, TypeError):
             pass # Handle potential parsing errors


    events = []
    for booking in bookings:
        # Prepare the data in FullCalendar's Event Object format
        # The 'title' is still useful for FullCalendar's internal use or list views.
        # We will use extendedProps for the custom display content.
        event_title = f"{booking.customer_name or 'Anonymous'} - {booking.service_type.name}"

        # Prepare extendedProps for custom rendering
        extended_props = {
            'customer_name': booking.customer_name or 'Anonymous',
            'service_type': booking.service_type.name,
            'status': booking.status,
            # Add vehicle details, checking if they exist
            # Make sure to adjust the following lines based on your actual ServiceBooking model structure
            'vehicle_make': getattr(booking, 'anon_vehicle_make', None) or (getattr(booking.vehicle, 'make', None) if hasattr(booking, 'vehicle') and booking.vehicle else None) or '',
            'vehicle_model': getattr(booking, 'anon_vehicle_model', None) or (getattr(booking.vehicle, 'model', None) if hasattr(booking, 'vehicle') and booking.vehicle else None) or '',
            'booking_id': booking.pk,
        }

        event = {
            'id': booking.pk,
            'title': event_title, # Standard FullCalendar title (can be used by list view, etc.)
            'start': booking.appointment_datetime.isoformat(),
            'url': reverse('dashboard:service_booking_details', args=[booking.pk]), # URL for event click
            'extendedProps': extended_props, # Custom data for our eventContent callback
        }
        events.append(event)

    return JsonResponse(events, safe=False)

# View for the service booking search page
@user_passes_test(is_staff_check)
def service_booking_search_view(request):
    query = request.GET.get('q')
    # Default sort matches the default option value in the template
    sort_by = request.GET.get('sort_by', '-appointment_datetime')

    # Get all possible status choices from the model
    booking_statuses = ServiceBooking.STATUS_CHOICES
    all_status_values = [status[0] for status in booking_statuses]

    # Determine the selected statuses
    # If 'status' is not in GET parameters, it's likely the initial load,
    # so select all statuses by default. Otherwise, get the list of selected statuses.
    if 'status' not in request.GET:
        selected_statuses = all_status_values
    else:
        selected_statuses = request.GET.getlist('status')


    bookings = ServiceBooking.objects.all()

    # --- Filtering by Status ---
    if selected_statuses:
         bookings = bookings.filter(status__in=selected_statuses)

    # --- Filtering by Search Query ---
    if query:
        # Start with an empty Q object for filtering
        search_filter = Q()

        # Add text field searches (case-insensitive contains)
        search_filter |= Q(customer_name__icontains=query)
        search_filter |= Q(customer_email__icontains=query)
        search_filter |= Q(customer_phone__icontains=query)
        search_filter |= Q(customer_address__icontains=query)
        search_filter |= Q(service_type__name__icontains=query)
        search_filter |= Q(customer_notes__icontains=query)
        search_filter |= Q(mechanic_notes__icontains=query)
        search_filter |= Q(anon_vehicle_make__icontains=query)
        search_filter |= Q(anon_vehicle_model__icontains=query)
        search_filter |= Q(anon_vehicle_vin_number__icontains=query)
        search_filter |= Q(anon_engine_number__icontains=query)
        search_filter |= Q(anon_vehicle_rego__icontains=query)
        search_filter |= Q(anon_vehicle_transmission__icontains=query)
        search_filter |= Q(booking_reference__icontains=query)
        
        bookings = bookings.filter(search_filter)

    # --- Sorting ---
    # Apply sorting based on values from the template
    if sort_by == 'id':
        bookings = bookings.order_by('id')
    elif sort_by == '-id':
        bookings = bookings.order_by('-id')
    elif sort_by == 'appointment_datetime':
        bookings = bookings.order_by('appointment_datetime')
    elif sort_by == '-appointment_datetime': # Default
        bookings = bookings.order_by('-appointment_datetime')
    elif sort_by == 'date_created':
        bookings = bookings.order_by('created_at')
    elif sort_by == '-date_created':
        bookings = bookings.order_by('-created_at')
    # No need for an else here, as sort_by has a default value

    context = {
        'page_title': 'Service Booking Search',
        'bookings': bookings,
        'query': query,
        'sort_by': sort_by,
        'selected_statuses': selected_statuses,
        'booking_statuses': booking_statuses,
    }
    return render(request, 'dashboard/service_booking_search.html', context) # Make sure this template name is correct
