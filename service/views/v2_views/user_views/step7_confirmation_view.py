from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from service.models import ServiceBooking
# Removed TempServiceBooking and convert_temp_service_booking imports
# as the conversion should now happen before this view.
from payments.models import Payment # Added for more robust processing check

class Step7ConfirmationView(View):
    """
    Handles the final step (Step 7) of the service booking process, displaying the confirmation page.
    This view expects the ServiceBooking to be already finalized (either in-store or online payment processed).
    If an online payment is pending (webhook delay), it will display a processing page.
    """
    def get(self, request):
        """
        Displays the booking confirmation details after payment or for in-store payment selections.

        It retrieves the ServiceBooking in one of two primary ways:
        1. From a 'final_service_booking_reference' stored in the session (for both in-store
           payments finalized in a previous step, or users returning to the page after online payment).
        2. From a 'payment_intent_id' passed in the URL (for initial landing after online payment,
           where webhook might still be processing).
        """
        service_booking = None
        is_processing = False  # Flag to indicate if booking is still being processed by webhook

        # 1. Try to retrieve the final booking reference from the session (preferred for all finalized bookings)
        booking_reference = request.session.get('final_service_booking_reference')
        if booking_reference:
            try:
                service_booking = ServiceBooking.objects.get(service_booking_reference=booking_reference)
            except ServiceBooking.DoesNotExist:
                # If session reference exists but booking doesn't, it might be an old/invalid reference.
                # Clear it and proceed to check payment_intent_id.
                del request.session['final_service_booking_reference']
                pass

        # 2. If not found in session, try to retrieve using payment_intent_id from URL (for online payments)
        payment_intent_id = request.GET.get('payment_intent_id')
        if not service_booking and payment_intent_id:
            try:
                # Attempt to find the ServiceBooking directly using the stripe_payment_intent_id
                service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
                # If found, store the reference in session for future use
                request.session['final_service_booking_reference'] = service_booking.service_booking_reference
                is_processing = False # Booking found, so not processing

            except ServiceBooking.DoesNotExist:
                # ServiceBooking not yet created. Now, check if a Payment object exists.
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    # If Payment exists, but ServiceBooking doesn't, it's genuinely processing.
                    is_processing = True
                except Payment.DoesNotExist:
                    # If neither ServiceBooking nor Payment exists, this payment_intent_id is invalid.
                    # Do NOT set is_processing to True. This will cause the final 'else' block to redirect.
                    is_processing = False
            except Exception:
                # If any other unexpected error occurs during ServiceBooking retrieval,
                # check if a Payment exists. If not, it's not processing.
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                except Payment.DoesNotExist:
                    is_processing = False


        # Determine the action based on whether a booking is found or still processing
        if service_booking:
            # Booking is confirmed, prepare context and render confirmation page
            # Clean up temporary session data if it still exists (e.g., from an earlier step)
            if 'temp_service_booking_uuid' in request.session:
                del request.session['temp_service_booking_uuid']

            context = {
                'service_booking': service_booking,
                'booking_status': service_booking.get_booking_status_display(),
                'payment_status': service_booking.get_payment_status_display(),
                'total_amount': service_booking.calculated_total,
                'amount_paid': service_booking.amount_paid,
                'currency': service_booking.currency,
                'motorcycle_details': f"{service_booking.customer_motorcycle.year} {service_booking.customer_motorcycle.brand} {service_booking.customer_motorcycle.model}",
                'customer_name': service_booking.service_profile.name,
                'is_processing': False, # Explicitly set to False as booking is found
            }
            return render(request, 'service/step7_confirmation.html', context)

        elif is_processing and payment_intent_id:
            # No final booking found yet, but we have a payment_intent_id AND Payment exists, so it's processing.
            # Render the page with a processing flag for AJAX polling.
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'service/step7_confirmation.html', context)
        else:
            # No booking found by session reference or payment_intent_id (or no payment for it),
            # and not in a processing state. This means the user should not be on this page.
            messages.warning(request, "Could not find a booking confirmation. Please start over if you have not booked.")
            return redirect('service:service')

