from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction
from inventory.mixins import AdminRequiredMixin
from inventory.models import SalesBooking

class SalesBookingDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        sales_booking = get_object_or_404(SalesBooking, pk=pk)
        motorcycle = sales_booking.motorcycle
        
        try:
            with transaction.atomic():
                booking_ref = sales_booking.sales_booking_reference
                sales_booking.delete()
                success_message = f'Sales booking {booking_ref} deleted successfully!'

                if motorcycle and motorcycle.status == 'reserved':
                    motorcycle.status = 'for_sale'
                    motorcycle.is_available = True
                    motorcycle.save()
                    success_message = f'Sales booking {booking_ref} deleted and motorcycle "{motorcycle}" is now available for sale.'

                messages.success(request, success_message)

        except Exception as e:
            messages.error(request, f'Error deleting sales booking {booking_ref}: {e}')
            
        return redirect('inventory:sales_bookings_management')
