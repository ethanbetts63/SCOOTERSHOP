# SCOOTER_SHOP/dashboard/views/delete_blocked_service_date.py

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import BlockedServiceDate

@user_passes_test(lambda u: u.is_staff)
def delete_blocked_service_date(request, pk):
    if request.method == 'POST':
        blocked_date = get_object_or_404(BlockedServiceDate, pk=pk)
        try:
            blocked_date.delete()
            messages.success(request, 'Blocked service date deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting blocked service date: {e}')
        return redirect('dashboard:blocked_service_dates_management')
    else:
        messages.error(request, 'Invalid request method for deleting a blocked date.')
        return redirect('dashboard:blocked_service_dates_management')