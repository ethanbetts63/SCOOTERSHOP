# inventory/views/user_views/initiate_booking_process_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction

from inventory.models import Motorcycle, TempSalesBooking # Ensure TempSalesBooking is imported

class InitiateBookingProcessView(View):
    def post(self, request, pk):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)

        # Retrieve the flag from the hidden input for deposit requirement
        deposit_required_for_flow_str = request.POST.get('deposit_required_for_flow', 'false')
        deposit_required_for_flow = (deposit_required_for_flow_str.lower() == 'true')

        # Retrieve the NEW flag for viewing request (default to false if not provided)
        request_viewing_str = request.POST.get('request_viewing', 'false')
        request_viewing = (request_viewing_str.lower() == 'true')

        with transaction.atomic():
            # Create the initial TempSalesBooking
            temp_booking = TempSalesBooking.objects.create(
                motorcycle=motorcycle,
                deposit_required_for_flow=deposit_required_for_flow,
                request_viewing=request_viewing, 
                booking_status='pending_details' 
            )

        # Store the temp_booking ID in the session for the next step
        request.session['current_temp_booking_id'] = temp_booking.pk

        # Redirect to the combined details and appointment form
        return redirect(reverse('inventory:step1_sales_profile')) # Ensure this URL name matches your urls.py