from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from inventory.models import SalesBooking
from payments.models import Payment # Needed to check if payment is processing


class Step4ConfirmationView(View):
    def get(self, request):
        sales_booking = None
        is_processing = False

        # Attempt to retrieve SalesBooking via session reference first (most direct after successful conversion)
        booking_reference = request.session.get('sales_booking_reference')
        if booking_reference:
            try:
                sales_booking = SalesBooking.objects.get(sales_booking_reference=booking_reference)
            except SalesBooking.DoesNotExist:
                # If booking_reference exists in session but booking is not found, clear it
                del request.session['sales_booking_reference']
                pass # Continue to check payment_intent_id

        # If not found by session reference, try via payment_intent_id from GET parameters (e.g., redirect from payment)
        payment_intent_id = request.GET.get('payment_intent_id')
        if not sales_booking and payment_intent_id:
            try:
                sales_booking = SalesBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
                # If found, set the session reference for direct access in future
                request.session['sales_booking_reference'] = sales_booking.sales_booking_reference
                is_processing = False # Booking is found, so no longer processing on this end

            except SalesBooking.DoesNotExist:
                # If SalesBooking not yet created (webhook still processing), check if Payment exists
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True # Payment exists, but booking conversion is pending
                   
                except Payment.DoesNotExist:
                    is_processing = False # Neither booking nor payment found for this intent
            except Exception as e:
                # Catch any other error during lookup, assume processing for safety if payment intent exists
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                except Payment.DoesNotExist:
                    is_processing = False


        if sales_booking:
            # Clean up temporary session UUID once permanent booking is established
            if 'temp_sales_booking_uuid' in request.session:
                del request.session['temp_sales_booking_uuid']

            context = {
                'sales_booking': sales_booking,
                'booking_status': sales_booking.get_booking_status_display(),
                'payment_status': sales_booking.get_payment_status_display(),
                'amount_paid': sales_booking.amount_paid,
                'currency': sales_booking.currency,
                'motorcycle_details': f"{sales_booking.motorcycle.year} {sales_booking.motorcycle.brand} {sales_booking.motorcycle.model}",
                'customer_name': sales_booking.sales_profile.name,
                'is_processing': False, # Confirmed booking found
                'motorcycle_price': sales_booking.motorcycle.price, # For displaying amount owing
            }
            return render(request, 'inventory/step4_confirmation.html', context)

        elif is_processing and payment_intent_id:
            # If payment is still processing via webhook, show a processing message
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'inventory/sales/step4_confirmation.html', context)
        else:
            # If no booking or ongoing payment found, redirect with a warning
            messages.warning(request, "Could not find a booking confirmation. Please start over if you have not booked.")
            return redirect('inventory:used')

