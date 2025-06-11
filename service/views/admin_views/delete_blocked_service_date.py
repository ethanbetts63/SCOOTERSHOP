# SCOOTER_SHOP/dashboard/views/delete_blocked_service_date.py

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from service.models import BlockedServiceDate

class BlockedServiceDateDeleteView(View):
    """
    Class-based view for deleting a specific blocked service date.
    Handles POST requests for deletion.
    """
    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests: deletes the BlockedServiceDate instance
        identified by the primary key (pk).
        """
        blocked_date = get_object_or_404(BlockedServiceDate, pk=pk)
        try:
            blocked_date.delete()
            messages.success(request, 'Blocked service date deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting blocked service date: {e}')
        # Redirect back to the management page after deletion
        return redirect('service:blocked_service_dates_management')

