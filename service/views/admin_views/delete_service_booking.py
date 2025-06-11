from django.views.generic import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import ServiceBooking

class AdminServiceBookingDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Admin view for deleting a ServiceBooking instance.
    Requires the user to be logged in and a staff member or superuser.
    """
    model = ServiceBooking
    template_name = 'service/admin_confirm_delete.html'  # You'll need to create this generic confirmation template
    success_url = reverse_lazy('service:service_booking_management')
    
    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, f"Booking {self.object.service_booking_reference} deleted successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error deleting the booking.")
        return super().form_invalid(form)