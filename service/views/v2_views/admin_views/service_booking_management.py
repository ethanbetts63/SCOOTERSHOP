# SCOOTER_SHOP/service/views/admin_views.py (continued from previous views)

import calendar
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime

from service.models import ServiceBooking, ServiceType, BlockedServiceDate # Ensure your model path is correct

class ServiceBookingManagementView(View):
    """
    Class-based view for displaying a list of all service bookings.
    This replaces the function-based service_bookings_view.
    """
    template_name = 'dashboard/service_bookings.html'

    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: retrieves all ServiceBooking objects and renders them.
        """
        bookings = ServiceBooking.objects.all().order_by('-appointment_date')

        context = {
            'page_title': 'Manage Service Bookings',
            'bookings': bookings,
            'active_tab': 'service_bookings' # Assuming this is for navigation highlighting
        }
        return render(request, self.template_name, context)

class ServiceBookingDetailsView(View):
    """
    Class-based view for displaying details of a single service booking.
    This replaces the function-based service_booking_details_view.
    """
    template_name = 'dashboard/service_booking_details.html' # Assuming this template exists
    
    def get(self, request, pk, *args, **kwargs):
        """
        Handles GET requests: retrieves a single ServiceBooking object by PK
        and renders its details.
        """
        booking = get_object_or_404(ServiceBooking, pk=pk)

        context = {
            'page_title': f'Service Booking Details - {booking.id}',
            'booking': booking,
            'active_tab': 'service_bookings'
        }
        return render(request, self.template_name, context)

class ServiceBookingJSONFeedView(View):
    """
    Class-based view that returns service bookings and blocked dates as a JSON feed
    for FullCalendar. This replaces the function-based get_service_bookings_json.
    """
    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: filters bookings and blocked dates by date range
        and returns them as a JSON response formatted for FullCalendar.
        """
        start_param = request.GET.get('start')
        end_param = request.GET.get('end')

        bookings = ServiceBooking.objects.all()
        blocked_service_dates = BlockedServiceDate.objects.all()

        start_date = None
        end_date = None

        if start_param and end_param:
            try:
                start_date = parse_datetime(start_param)
                end_date = parse_datetime(end_param)

                if start_date and end_date:
                    bookings = bookings.filter(
                        appointment_date__gte=start_date,
                        appointment_date__lt=end_date
                    )
                    blocked_service_dates = blocked_service_dates.filter(
                        start_date__lte=end_date.date(),
                        end_date__gte=start_date.date()
                    )
            except (ValueError, TypeError):
                pass

        events = []
        # Add booking events
        for booking in bookings:
            event_title = f"{booking.service_profile.name or 'Anonymous'} - {booking.service_type.name}"

            extended_props = {
                'customer_name': booking.service_profile.name or 'Anonymous',
                'service_type': booking.service_type.name,
                'status': booking.booking_status, # Use booking_status from the ServiceBooking model
                'vehicle_make': booking.customer_motorcycle.make if booking.customer_motorcycle else '',
                'vehicle_model': booking.customer_motorcycle.model if booking.customer_motorcycle else '',
                'booking_id': booking.pk,
            }

            event = {
                'id': booking.pk,
                'title': event_title,
                'start': booking.dropoff_date.isoformat(), # Use dropoff_date
                'url': reverse('service:service_booking_details', args=[booking.pk]),
                'extendedProps': extended_props,
            }
            events.append(event)

        # Add blocked date events
        for blocked_service_date_range in blocked_service_dates:
            current_date = blocked_service_date_range.start_date
            while current_date <= blocked_service_date_range.end_date:
                blocked_event = {
                    'start': current_date.isoformat(),
                    'title': 'Blocked Day',
                    'extendedProps': {
                        'is_blocked': True,
                        'description': blocked_service_date_range.description,
                    },
                    'className': 'blocked-date-tile',
                    'display': 'block',
                }
                events.append(blocked_event)
                current_date += timedelta(days=1)

        return JsonResponse(events, safe=False)

class ServiceBookingSearchView(View):
    """
    Class-based view for the service booking search page.
    This replaces the function-based service_booking_search_view.
    """
    template_name = 'dashboard/service_booking_search.html' # Assuming this template exists

    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: filters and sorts service bookings based on
        search query and status.
        """
        query = request.GET.get('q')
        sort_by = request.GET.get('sort_by', '-dropoff_date') # Default to dropoff_date
        
        # Get all possible status choices from the model
        booking_statuses = ServiceBooking.BOOKING_STATUS_CHOICES # Assuming this is the correct attribute name
        all_status_values = [status[0] for status in booking_statuses]

        if 'status' not in request.GET:
            selected_statuses = all_status_values
        else:
            selected_statuses = request.GET.getlist('status')

        bookings = ServiceBooking.objects.all()

        # --- Filtering by Status ---
        if selected_statuses:
            bookings = bookings.filter(booking_status__in=selected_statuses) # Filter by booking_status

        # --- Filtering by Search Query ---
        if query:
            search_filter = Q()
            search_filter |= Q(service_profile__name__icontains=query)
            search_filter |= Q(service_profile__email__icontains=query)
            search_filter |= Q(service_profile__phone_number__icontains=query)
            search_filter |= Q(service_profile__address_line_1__icontains=query)
            search_filter |= Q(service_type__name__icontains=query)
            search_filter |= Q(customer_notes__icontains=query)
            # Assuming mechanic_notes is on ServiceBooking
            search_filter |= Q(mechanic_notes__icontains=query) 

            # For customer_motorcycle fields, use __ notation
            search_filter |= Q(customer_motorcycle__make__icontains=query)
            search_filter |= Q(customer_motorcycle__model__icontains=query)
            search_filter |= Q(customer_motorcycle__vin_number__icontains=query)
            search_filter |= Q(customer_motorcycle__engine_number__icontains=query)
            search_filter |= Q(customer_motorcycle__rego__icontains=query)
            search_filter |= Q(customer_motorcycle__transmission__icontains=query)
            
            # Assuming booking_reference is on ServiceBooking
            search_filter |= Q(booking_reference__icontains=query)

            bookings = bookings.filter(search_filter)

        # --- Sorting ---
        if sort_by == 'id':
            bookings = bookings.order_by('id')
        elif sort_by == '-id':
            bookings = bookings.order_by('-id')
        elif sort_by == 'dropoff_date': # Changed from appointment_date
            bookings = bookings.order_by('dropoff_date')
        elif sort_by == '-dropoff_date': # Changed from appointment_date
            bookings = bookings.order_by('-dropoff_date')
        elif sort_by == 'date_created':
            bookings = bookings.order_by('created_at')
        elif sort_by == '-date_created':
            bookings = bookings.order_by('-created_at')

        context = {
            'page_title': 'Service Booking Search',
            'bookings': bookings,
            'query': query,
            'sort_by': sort_by,
            'selected_statuses': selected_statuses,
            'booking_statuses': booking_statuses,
            'active_tab': 'service_bookings'
        }
        return render(request, self.template_name, context)

