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

from service.models import ServiceBooking, ServiceType

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
    return render(request, 'dashboard/service_bookings.html', context)

# View for displaying details of a single service booking
@user_passes_test(is_staff_check)
def service_booking_details_view(request, pk):
    booking = get_object_or_404(ServiceBooking, pk=pk)

    context = {
        'page_title': f'Service Booking Details - {booking.id}',
        'booking': booking,
    }
    return render(request, 'dashboard/service_booking_details.html', context)

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
        event = {
            'id': booking.pk,
            'title': f"{booking.customer_name or 'Anonymous'} - {booking.service_type.name}",
            'start': booking.appointment_datetime.isoformat(),
            'url': reverse('dashboard:service_booking_details', args=[booking.pk]),
            'status': booking.status,
            'color': 'blue' if booking.status == 'confirmed' else ('orange' if booking.status == 'pending' else 'red'),
            'customer_name': booking.customer_name,
            'service_type': booking.service_type.name,
        }
        events.append(event)

    return JsonResponse(events, safe=False)

# View for the service booking search page
@user_passes_test(is_staff_check)
def service_booking_search_view(request):
    query = request.GET.get('q')
    bookings = ServiceBooking.objects.all().order_by('-appointment_datetime')

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
        search_filter |= Q(status__icontains=query)

        # Attempt to add booking ID search if query is a valid integer
        try:
            query_as_int = int(query)
            search_filter |= Q(pk=query_as_int) # Add exact match for pk
        except ValueError:
            pass # Skip pk search if query is not an integer

        # Apply the combined filter to the queryset
        bookings = bookings.filter(search_filter)

    context = {
        'page_title': 'Service Booking Search',
        'bookings': bookings,
        'query': query 
    }
    return render(request, 'dashboard/service_booking_search.html', context)