from django.shortcuts import render
from django.views import View
from django.db.models import Q

class ServiceBookingSearchView(View):
    """
    Class-based view for the service booking search page.
    This replaces the function-based service_booking_search_view.
    """
    template_name = 'dashboard/service_booking_search.html' # Assuming this template exists

    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):\
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
            # Check if 'mechanic_notes' field exists before filtering
            if hasattr(ServiceBooking, 'mechanic_notes'):
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
        elif sort_by == 'dropoff_date': # Already changed to dropoff_date
            bookings = bookings.order_by('dropoff_date')
        elif sort_by == '-dropoff_date': # Already changed to dropoff_date
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
