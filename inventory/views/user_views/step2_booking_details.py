from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
import json # Import the json module

from inventory.models import TempSalesBooking, InventorySettings, SalesBooking, SalesProfile
from inventory.forms.sales_booking_appointment_form import BookingAppointmentForm
# Import the new utility function
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking

class Step2BookingDetailsView(View):
    template_name = 'inventory/step2_booking_details.html'

    def get(self, request, *args, **kwargs):
        print(f"--- Entering Step2BookingDetailsView GET method ---")
        print(f"Session data at start: {request.session.keys()}") # Print all session keys

        # 1. Retrieve temp_sales_booking_uuid from session.
        # This now expects the UUID string stored by initiate_booking_process_view.
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')
        print(f"DEBUG (Step2 GET): Retrieved 'temp_sales_booking_uuid': {temp_booking_uuid}")

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            print("DEBUG (Step2 GET): No temp_sales_booking_uuid found in session.")
            return redirect(reverse('core:index')) # Or redirect to where the process starts

        # 2. Fetch TempSalesBooking instance using session_uuid, not pk.
        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
            print(f"DEBUG (Step2 GET): Successfully fetched TempSalesBooking PK: {temp_booking.pk}, UUID: {temp_booking.session_uuid}")
        except Exception as e:
            messages.error(request, f"Your booking session could not be found or is invalid. Error: {e}")
            print(f"ERROR (Step2 GET): Failed to fetch TempSalesBooking with UUID {temp_booking_uuid}. Error: {e}")
            return redirect(reverse('core:index')) # Or redirect to where the process starts


        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            print("DEBUG (Step2 GET): InventorySettings not found.")
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

        # Call the new utility to get min_date, max_date, and blocked_dates
        min_date_obj, max_date_obj, blocked_dates_list = get_sales_appointment_date_info(
            inventory_settings, temp_booking.deposit_required_for_flow
        )
        
        # Convert date objects to string format for Flatpickr and JSON serialization
        min_date_str = min_date_obj.strftime('%Y-%m-%d')
        max_date_str = max_date_obj.strftime('%Y-%m-%d')
        blocked_dates_json = json.dumps(blocked_dates_list)

        context = {
            'form': form,
            'temp_booking': temp_booking,
            'inventory_settings': inventory_settings,
            'min_appointment_date': min_date_str,             # Pass min date string
            'max_appointment_date': max_date_str,             # Pass max date string
            'blocked_appointment_dates_json': blocked_dates_json, # Pass JSON string of blocked dates
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        print(f"--- Entering Step2BookingDetailsView POST method ---")
        print(f"Session data at start: {request.session.keys()}") # Print all session keys

        # 1. Retrieve temp_sales_booking_uuid from session.
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')
        print(f"DEBUG (Step2 POST): Retrieved 'temp_sales_booking_uuid': {temp_booking_uuid}")

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            print("DEBUG (Step2 POST): No temp_sales_booking_uuid found in session.")
            return redirect(reverse('core:index'))

        # 2. Fetch TempSalesBooking instance using session_uuid.
        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
            print(f"DEBUG (Step2 POST): Successfully fetched TempSalesBooking PK: {temp_booking.pk}, UUID: {temp_booking.session_uuid}")
        except Exception as e:
            messages.error(request, f"Your booking session could not be found or is invalid. Error: {e}")
            print(f"ERROR (Step2 POST): Failed to fetch TempSalesBooking with UUID {temp_booking_uuid}. Error: {e}")
            return redirect(reverse('core:index'))


        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            print("DEBUG (Step2 POST): InventorySettings not found.")
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
                print(f"DEBUG (Step2 POST): TempSalesBooking details saved. UUID: {temp_booking.session_uuid}")


                if temp_booking.deposit_required_for_flow:
                    messages.success(request, "Booking details saved. Proceed to payment.")
                    # No longer deleting 'current_temp_booking_id' as we're using 'temp_sales_booking_uuid'
                    print(f"DEBUG (Step2 POST): Deposit required, redirecting to step3_payment.")
                    return redirect(reverse('inventory:step3_payment'))
                else:
                    converted_sales_booking = convert_temp_sales_booking(
                        temp_booking=temp_booking,
                        booking_payment_status='unpaid',
                        amount_paid_on_booking=Decimal('0.00'),
                        stripe_payment_intent_id=None,
                        payment_obj=None,
                    )
                    # Clean up the temp_sales_booking_uuid from session upon conversion to final SalesBooking
                    if 'temp_sales_booking_uuid' in request.session:
                        del request.session['temp_sales_booking_uuid']
                        print("DEBUG (Step2 POST): 'temp_sales_booking_uuid' cleared from session after conversion.")

                    # This line below seems to refer to an old session key.
                    # Ensure you're storing the *new* sales booking reference correctly if needed.
                    # If SalesBooking has its own reference, store that.
                    request.session['current_sales_booking_reference'] = converted_sales_booking.sales_booking_reference
                    print(f"DEBUG (Step2 POST): Converted to SalesBooking. New sales_booking_reference stored: {converted_sales_booking.sales_booking_reference}")


                    messages.success(request, "Your enquiry has been submitted. We will get back to you shortly!")
                    return redirect(reverse('inventory:confirmation_page'))
        else:
            # If form is invalid, re-render with errors AND pass date info again
            print(f"DEBUG (Step2 POST): Form is invalid. Errors: {form.errors}")
            min_date_obj, max_date_obj, blocked_dates_list = get_sales_appointment_date_info(
                inventory_settings, temp_booking.deposit_required_for_flow
            )
            min_date_str = min_date_obj.strftime('%Y-%m-%d')
            max_date_str = max_date_obj.strftime('%Y-%m-%d')
            blocked_dates_json = json.dumps(blocked_dates_list)

            context = {
                'form': form,
                'temp_booking': temp_booking,
                'inventory_settings': inventory_settings,
                'min_appointment_date': min_date_str,
                'max_appointment_date': max_date_str,
                'blocked_appointment_dates_json': blocked_dates_json,
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)

