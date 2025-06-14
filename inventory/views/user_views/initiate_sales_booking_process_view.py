from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from inventory.models import Motorcycle, TempSalesBooking, InventorySettings
from decimal import Decimal
from django.contrib import messages

class InitiateBookingProcessView(View):
    def post(self, request, pk):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)

        deposit_required_for_flow_str = request.POST.get('deposit_required_for_flow', 'false')
        deposit_required_for_flow = (deposit_required_for_flow_str.lower() == 'true')

        request_viewing_str = request.POST.get('request_viewing', 'false')
        request_viewing = (request_viewing_str.lower() == 'true')

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('inventory:all'))

        with transaction.atomic():
            temp_booking = TempSalesBooking(
                motorcycle=motorcycle,
                deposit_required_for_flow=deposit_required_for_flow,
                request_viewing=request_viewing,
                booking_status='pending_details'
            )

            if deposit_required_for_flow:
                temp_booking.amount_paid = inventory_settings.deposit_amount
            else:
                temp_booking.amount_paid = Decimal('0.00')

            temp_booking.save()

        request.session['temp_sales_booking_uuid'] = str(temp_booking.session_uuid)

        return redirect(reverse('inventory:step1_sales_profile'))
