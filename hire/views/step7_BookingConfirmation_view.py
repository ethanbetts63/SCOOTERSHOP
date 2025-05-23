# hire/views/step7_BookingConfirmation_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from hire.models import HireBooking # We will display the final HireBooking
from payments.models import Payment # Import the Payment model
import logging

logger = logging.getLogger(__name__)

class BookingConfirmationView(View):
    def get(self, request):
        """
        Displays the booking confirmation details after successful payment.
        It can retrieve the HireBooking either from the session's booking_reference
        or from a payment_intent_id passed in the URL query parameters.
        """
        logger.debug("Entering BookingConfirmationView GET method.")

        hire_booking = None
        is_processing = False # Flag to indicate if booking is still being processed by webhook

        # 1. Try to retrieve the final booking reference from the session (preferred)
        booking_reference = request.session.get('final_booking_reference')
        if booking_reference:
            try:
                hire_booking = get_object_or_404(HireBooking, booking_reference=booking_reference)
                logger.debug(f"Retrieved HireBooking from session: {hire_booking.booking_reference}")
            except HireBooking.DoesNotExist:
                logger.debug(f"HireBooking with reference {booking_reference} not found in DB, despite being in session. Falling back to payment_intent_id.")
        else:
            logger.debug("No final_booking_reference in session.")

        # 2. If not found in session, try to retrieve using payment_intent_id from URL
        payment_intent_id = request.GET.get('payment_intent_id')
        if not hire_booking and payment_intent_id:
            logger.debug(f"Attempting to retrieve HireBooking using payment_intent_id: {payment_intent_id}")
            try:
                # Find the Payment object first
                payment_obj = get_object_or_404(Payment, stripe_payment_intent_id=payment_intent_id)
                # Then get the associated HireBooking
                hire_booking = get_object_or_404(HireBooking, payment=payment_obj)
                logger.debug(f"Retrieved HireBooking from Payment object: {hire_booking.booking_reference}")

                # If found this way, store the booking_reference in session for future use
                request.session['final_booking_reference'] = hire_booking.booking_reference
                logger.debug(f"Stored final_booking_reference: {hire_booking.booking_reference} in session for future use.")

            except Payment.DoesNotExist:
                logger.warning(f"Payment object with intent ID {payment_intent_id} not found. Booking likely not finalized yet.")
                is_processing = True # Set flag for client-side polling
            except HireBooking.DoesNotExist:
                logger.warning(f"HireBooking not found for Payment object with intent ID {payment_intent_id}. Booking likely not finalized yet.")
                is_processing = True # Set flag for client-side polling
        elif not hire_booking and not payment_intent_id:
            logger.debug("No payment_intent_id in URL query parameters and no booking_reference in session. Redirecting to step 2.")
            return redirect('hire:step2_choose_bike')

        # If after both attempts, no booking is found, and we have a payment_intent_id,
        # it means the webhook hasn't processed it yet. Render the page with a processing flag.
        if not hire_booking and is_processing:
            logger.info(f"HireBooking not yet available for payment_intent_id {payment_intent_id}. Rendering processing state.")
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'hire/step7_booking_confirmation.html', context)
        elif not hire_booking: # No booking found and no payment_intent_id to poll
            logger.debug("No HireBooking found by session or payment_intent_id. Redirecting to step 2.")
            return redirect('hire:step2_choose_bike')


        # Clear the session variable as the booking is now confirmed and persistent
        if 'final_booking_reference' in request.session:
            del request.session['final_booking_reference']
            logger.debug("Cleared 'final_booking_reference' from session.")

        # Also clear the temp_booking_id if it somehow still exists here
        if 'temp_booking_id' in request.session:
            del request.session['temp_booking_id']
            logger.debug("Cleared 'temp_booking_id' from session.")


        context = {
            'hire_booking': hire_booking,
            'booking_status': hire_booking.status,
            'payment_status': hire_booking.payment_status,
            'total_price': hire_booking.total_price,
            'amount_paid': hire_booking.amount_paid,
            'currency': hire_booking.currency,
            'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
            'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
            'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
            'driver_name': hire_booking.driver_profile.name,
            'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
            'addons': hire_booking.booking_addons.all(),
            'is_processing': False, # Explicitly set to False when booking is found
        }
        logger.debug("Rendering step7_booking_confirmation.html with context.")
        return render(request, 'hire/step7_booking_confirmation.html', context)


class BookingStatusCheckView(View):
    def get(self, request):
        """
        AJAX endpoint to check the status of a HireBooking based on payment_intent_id.
        Returns JSON indicating if the booking is ready or still processing.
        """
        payment_intent_id = request.GET.get('payment_intent_id')
        logger.debug(f"Entering BookingStatusCheckView GET method for payment_intent_id: {payment_intent_id}")

        if not payment_intent_id:
            logger.error("No payment_intent_id provided for status check.")
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required'}, status=400)

        try:
            payment_obj = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
            hire_booking = HireBooking.objects.get(payment=payment_obj)

            # If HireBooking is found, return its details
            response_data = {
                'status': 'ready',
                'booking_reference': hire_booking.booking_reference,
                'booking_status': hire_booking.status,
                'payment_status': hire_booking.payment_status,
                'total_price': str(hire_booking.total_price), # Convert Decimal to string for JSON
                'amount_paid': str(hire_booking.amount_paid),
                'currency': hire_booking.currency,
                'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
                'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
                'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
                'driver_name': hire_booking.driver_profile.name,
                'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
                'addons': [{'name': addon.addon.name, 'quantity': addon.quantity, 'price': str(addon.price_at_booking)} for addon in hire_booking.booking_addons.all()],
            }
            logger.debug(f"Booking found for {payment_intent_id}. Status: ready.")
            return JsonResponse(response_data)

        except Payment.DoesNotExist:
            logger.info(f"Payment object not yet found for intent ID {payment_intent_id}. Still processing.")
            return JsonResponse({'status': 'processing', 'message': 'Payment record not yet available.'})
        except HireBooking.DoesNotExist:
            logger.info(f"HireBooking not yet found for payment intent ID {payment_intent_id}. Still processing.")
            return JsonResponse({'status': 'processing', 'message': 'Booking still being finalized.'})
        except Exception as e:
            logger.exception(f"An unexpected error occurred during status check for {payment_intent_id}: {e}")
            return JsonResponse({'status': 'error', 'message': 'An internal server error occurred during status check.'}, status=500)

