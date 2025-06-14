# SCOOTER_SHOP/inventory/views/admin_views/sales_booking_delete_view.py

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin

from inventory.models import SalesBooking

class SalesBookingDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        sales_booking = get_object_or_404(SalesBooking, pk=pk)
        try:
            booking_ref = sales_booking.sales_booking_reference
            sales_booking.delete()
            messages.success(request, f'Sales booking {booking_ref} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting sales booking {sales_booking.sales_booking_reference}: {e}')
        return redirect('inventory:sales_bookings_management')
