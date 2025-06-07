
from datetime import timedelta
from django.views import View
from django.urls import reverse
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from service.models import ServiceBooking, BlockedServiceDate

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
                        # Changed from 'appointment_date__gte' to 'dropoff_date__gte'
                        dropoff_date__gte=start_date,
                        # Changed from 'appointment_date__lt' to 'dropoff_date__lt'
                        dropoff_date__lt=end_date
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
                        # Changed from 'appointment_date__gte' to 'dropoff_date__gte'
                        dropoff_date__gte=start_date,
                        # Changed from 'appointment_date__lt' to 'dropoff_date__lt'
                        dropoff_date__lt=end_date
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

