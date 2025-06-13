from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
import json # Import the json module

from inventory.models import TempSalesBooking, InventorySettings, SalesBooking, SalesProfile
from inventory.forms.sales_booking_appointment_form import BookingAppointmentForm
from inventory.utils.get_available_appointment_dates import get_available_appointment_dates
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking

class Step2BookingDetailsView(View):
    template_name = 'inventory/step2_booking_details.html'

    def get(self, request, *args, **kwargs):
        temp_booking_id = request.session.get('current_temp_booking_id')
        if not temp_booking_id:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('core:index'))

        temp_booking = get_object_or_404(TempSalesBooking, pk=temp_booking_id)

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('core:index'))

        initial_data = {
            'request_viewing': 'yes' if temp_booking.request_viewing else 'no',
            'appointment_date': temp_booking.appointment_date,
            'appointment_time': temp_booking.appointment_time,
            'customer_notes': temp_booking.customer_notes,
            'terms_accepted': temp_booking.terms_accepted,
        }

        form = BookingAppointmentForm(
            initial=initial_data,
            deposit_required_for_flow=temp_booking.deposit_required_for_flow,
            inventory_settings=inventory_settings
        )

        available_dates = get_available_appointment_dates(inventory_settings, temp_booking.deposit_required_for_flow)
        
        # Convert the list of dates to a JSON string using json.dumps
        # This ensures proper double quotes for JavaScript parsing
        available_dates_json = json.dumps([d.strftime('%Y-%m-%d') for d in available_dates])

        context = {
            'form': form,
            'temp_booking': temp_booking,
            'inventory_settings': inventory_settings,
            'available_dates': available_dates_json, # Pass the JSON string here
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_booking_id = request.session.get('current_temp_booking_id')
        if not temp_booking_id:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('core:index'))

        temp_booking = get_object_or_404(TempSalesBooking, pk=temp_booking_id)

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('core:index'))

        form = BookingAppointmentForm(
            request.POST,
            deposit_required_for_flow=temp_booking.deposit_required_for_flow,
            inventory_settings=inventory_settings
        )

        if form.is_valid():
            with transaction.atomic():
                customer_notes = form.cleaned_data.get('customer_notes')
                request_viewing = form.cleaned_data.get('request_viewing')
                appointment_date = form.cleaned_data.get('appointment_date')
                appointment_time = form.cleaned_data.get('appointment_time')
                terms_accepted = form.cleaned_data.get('terms_accepted')

                temp_booking.customer_notes = customer_notes
                temp_booking.request_viewing = request_viewing
                temp_booking.appointment_date = appointment_date
                temp_booking.appointment_time = appointment_time
                temp_booking.terms_accepted = terms_accepted
                temp_booking.save()

                if temp_booking.deposit_required_for_flow:
                    messages.success(request, "Booking details saved. Proceed to payment.")
                    return redirect(reverse('inventory:payment_page'))
                else:
                    converted_sales_booking = convert_temp_sales_booking(
                        temp_booking=temp_booking,
                        booking_payment_status='unpaid',
                        amount_paid_on_booking=Decimal('0.00'),
                        stripe_payment_intent_id=None,
                        payment_obj=None,
                    )
                    if 'current_temp_booking_id' in request.session:
                        del request.session['current_temp_booking_id']
                    request.session['current_sales_booking_reference'] = converted_sales_booking.sales_booking_reference

                    messages.success(request, "Your enquiry has been submitted. We will get back to you shortly!")
                    return redirect(reverse('inventory:confirmation_page'))
        else:
            available_dates = get_available_appointment_dates(inventory_settings, temp_booking.deposit_required_for_flow)
            available_dates_json = json.dumps([d.strftime('%Y-%m-%d') for d in available_dates])
            context = {
                'form': form,
                'temp_booking': temp_booking,
                'inventory_settings': inventory_settings,
                'available_dates': available_dates_json, # Pass the JSON string here
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
