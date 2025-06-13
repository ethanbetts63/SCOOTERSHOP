from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction

# Assuming these models are accessible
from inventory.models import Motorcycle
from inventory.models import TempSalesBooking
# from .forms import SalesProfileForm, TempSalesBookingDetailsForm # Will define these later

class InitiateBookingProcessView(View):
    def post(self, request, pk):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)

        # Retrieve the flag from the hidden input
        deposit_required_for_flow_str = request.POST.get('deposit_required_for_flow', 'false')
        deposit_required_for_flow = (deposit_required_for_flow_str.lower() == 'true')

        with transaction.atomic():
            # Create the initial TempSalesBooking
            temp_booking = TempSalesBooking.objects.create(
                motorcycle=motorcycle,
                deposit_required_for_flow=deposit_required_for_flow,
                # No sales_profile or appointment details yet
                booking_status='pending_details' # A new status for this initial state
            )

        # Store the temp_booking ID in the session for the next step
        request.session['current_temp_booking_id'] = temp_booking.pk

        # Redirect to the combined details and appointment form
        return redirect(reverse('booking_details_and_appointment'))
