# inventory/views/user_views/initiate_booking_process_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction

from inventory.models import Motorcycle, TempSalesBooking, InventorySettings # Import InventorySettings
from decimal import Decimal # Import Decimal for working with money

class InitiateBookingProcessView(View):
    def post(self, request, pk):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)

        # Retrieve the flag from the hidden input for deposit requirement
        deposit_required_for_flow_str = request.POST.get('deposit_required_for_flow', 'false')
        deposit_required_for_flow = (deposit_required_for_flow_str.lower() == 'true')

        # Retrieve the NEW flag for viewing request (default to false if not provided)
        request_viewing_str = request.POST.get('request_viewing', 'false')
        request_viewing = (request_viewing_str.lower() == 'true')

        # Fetch InventorySettings to get the deposit amount if needed
        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            # Handle this case, perhaps redirect to an error page or show a message
            # For now, let's assume it exists or raise an error for debugging
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('inventory:all')) # Redirect to a safe page

        with transaction.atomic():
            # Create the initial TempSalesBooking instance
            temp_booking = TempSalesBooking(
                motorcycle=motorcycle,
                deposit_required_for_flow=deposit_required_for_flow,
                request_viewing=request_viewing,
                booking_status='pending_details'
            )

            # Set the amount_paid if a deposit is required for this flow
            if deposit_required_for_flow:
                temp_booking.amount_paid = inventory_settings.deposit_amount
            else:
                temp_booking.amount_paid = Decimal('0.00') # Ensure it's explicitly 0 if no deposit

            temp_booking.save() # Save the temp_booking after setting amount_paid

        # Store the temp_booking's actual session_uuid in the session for the next step.
        request.session['temp_sales_booking_uuid'] = str(temp_booking.session_uuid)

        # Redirect to the combined details and appointment form
        return redirect(reverse('inventory:step1_sales_profile'))
