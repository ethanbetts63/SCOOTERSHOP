                                                                    

from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import ServiceBooking

class AdminServiceBookingDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Displays the details of a specific Service Booking for admin users.
    This view uses the existing AJAX endpoint to fetch the data.
    """
    model = ServiceBooking
    template_name = 'service/admin_service_booking_detail.html'
    context_object_name = 'service_booking'                                         

    def test_func(self):
        """
        Ensures that only staff users can access this view.
        """
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        """
        Adds the booking's primary key to the context for the template.
        """
        context = super().get_context_data(**kwargs)
                                                                                              
        context['booking_pk'] = self.object.pk 
        return context


