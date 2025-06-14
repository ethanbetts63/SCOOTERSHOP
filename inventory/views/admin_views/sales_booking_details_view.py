# SCOOTER_SHOP/inventory/views/admin_views/sales_booking_details_view.py

from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.models import SalesBooking

class SalesBookingDetailsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = SalesBooking
    template_name = 'inventory/admin_sales_booking_details.html'
    context_object_name = 'sales_booking'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Sales Booking Details: {self.object.sales_booking_reference}"
        return context

