from django.shortcuts import render
from django.views import View

from service.models import ServiceBooking, ServiceType, BlockedServiceDate                                    

class ServiceBookingManagementView(View):
    """
    Class-based view for displaying a list of all service bookings.
    This replaces the function-based service_bookings_view.
    """
    template_name = 'service/service_booking_management.html'

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: retrieves all ServiceBooking objects and renders them.
        """
                                                                        
                                             
                                                                          
        bookings = ServiceBooking.objects.all().order_by('-dropoff_date')

        context = {
            'page_title': 'Manage Service Bookings',
            'bookings': bookings,                                                                        
            'active_tab': 'service_bookings'                                               
        }
        return render(request, self.template_name, context)

