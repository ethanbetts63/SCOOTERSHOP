from django.shortcuts import render, get_object_or_404
from django.views import View
from service.models import ServiceBooking


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
