# hire/views/step7_BookingConfirmation_view.py
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from hire.models import HireBooking
from payments.models import Payment
# Removed import logging as it's no longer used in this file

class BookingConfirmationView(View):
    def get(self, request):
        """
        Displays the booking confirmation details after successful payment.
        It can retrieve the HireBooking either from the session's booking_reference
        (for in-store payments) or from a payment_intent_id passed in the URL query parameters
        (for online payments).
        """
        hire_booking = None
        is_processing = False # Flag to indicate if booking is still being processed by webhook

        # 1. Try to retrieve the final booking reference from the session (preferred for in-store)
        booking_reference = request.session.get('final_booking_reference')
        if booking_reference:
            try:
                # Use .get() instead of get_object_or_404 to catch DoesNotExist
                hire_booking = HireBooking.objects.get(booking_reference=booking_reference)
            except HireBooking.DoesNotExist:
                pass # Silently fail and proceed to next check
        
        # 2. If not found in session, try to retrieve using payment_intent_id from URL (for online payments)
        payment_intent_id = request.GET.get('payment_intent_id')
        if not hire_booking and payment_intent_id:
            try:
                # Try to find the HireBooking directly using the stripe_payment_intent_id
                hire_booking = HireBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

                # If found this way, store the booking_reference in session for future use
                # This is important for subsequent page loads or refreshes.
                request.session['final_booking_reference'] = hire_booking.booking_reference

            except HireBooking.DoesNotExist:
                is_processing = True # Set flag for client-side polling
            except Exception as e:
                # If any other unexpected error, treat as processing and let polling handle it
                is_processing = True
        elif not hire_booking and not payment_intent_id and not booking_reference: # No booking found and no identifier to poll
            return redirect('hire:step2_choose_bike')


        # If after both attempts, no booking is found, and we have a payment_intent_id,
        # it means the webhook hasn't processed it yet. Render the page with a processing flag.
        if not hire_booking and is_processing:
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'hire/step7_booking_confirmation.html', context)
        elif not hire_booking: # This case should ideally not be reached if previous checks are robust
            return redirect('hire:step2_choose_bike')


        # --- REMOVED: Clearing 'final_booking_reference' here. ---
        # It should persist in the session after a successful display,
        # especially if the user refreshes the page.
        # It can be cleared when the user moves to a different part of the site
        # or when the session expires.
        # if 'final_booking_reference' in request.session:
        #     del request.session['final_booking_reference']

        # Also clear the temp_booking_id if it somehow still exists here
        if 'temp_booking_id' in request.session:
            del request.session['temp_booking_id']


        context = {
            'hire_booking': hire_booking,
            'booking_status': hire_booking.status,
            'payment_status': hire_booking.payment_status,
            'grand_total': hire_booking.grand_total,
            'amount_paid': hire_booking.amount_paid,
            'currency': hire_booking.currency,
            'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
            'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
            'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
            'driver_name': hire_booking.driver_profile.name,
            'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
            'addons': hire_booking.booking_addons.all(),
            'is_processing': False,
        }
        return render(request, 'hire/step7_booking_confirmation.html', context)


class BookingStatusCheckView(View):
    def get(self, request):
        """
        AJAX endpoint to check the status of a HireBooking based on payment_intent_id.
        Returns JSON indicating if the booking is ready or still processing.
        """
        payment_intent_id = request.GET.get('payment_intent_id')

        if not payment_intent_id:
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required'}, status=400)

        try:
            # Try to find the HireBooking directly using the stripe_payment_intent_id
            hire_booking = HireBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

            # If HireBooking is found, return its details
            response_data = {
                'status': 'ready',
                'booking_reference': hire_booking.booking_reference,
                'booking_status': hire_booking.status,
                'payment_status': hire_booking.payment_status,
                'grand_total': str(hire_booking.grand_total),
                'amount_paid': str(hire_booking.amount_paid),
                'currency': hire_booking.currency,
                'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
                'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
                'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
                'driver_name': hire_booking.driver_profile.name,
                'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
                'addons': [{'name': addon.addon.name, 'quantity': addon.quantity, 'price': str(addon.booked_addon_price)} for addon in hire_booking.booking_addons.all()],
            }
            return JsonResponse(response_data)

        except HireBooking.DoesNotExist:
            # If HireBooking is not found, check if the Payment object still exists.
            # This helps differentiate between "not yet processed" and "processed but failed to create HireBooking"
            try:
                Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                return JsonResponse({'status': 'processing', 'message': 'Booking still being finalized.'})
            except Payment.DoesNotExist:
                # If both Payment and HireBooking are gone, it implies a problem in the webhook handler
                # where TempHireBooking was deleted but HireBooking was not created.
                # In this specific scenario, we should return an error or a "failed" status
                # to the client, as the booking cannot be confirmed.
                return JsonResponse({'status': 'error', 'message': 'Booking finalization failed. Please contact support.'}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'An internal server error occurred during status check.'}, status=500)
