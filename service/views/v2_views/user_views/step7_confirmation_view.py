from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from service.models import ServiceBooking, TempServiceBooking
from service.utils import convert_temp_service_booking

class Step7ConfirmationView(View):
    """
    Handles the final step (Step 7) of the service booking process, displaying the confirmation page.
    """
    def get(self, request):
        """
        Displays the booking confirmation details after payment or for in-store payment selections.

        It retrieves the ServiceBooking in one of several ways:
        1. For 'in-store' payments: It uses a 'temp_booking_uuid' from the URL to find the
           temporary booking, converts it to a final ServiceBooking, and then displays it.
        2. For completed online payments: It uses a 'payment_intent_id' from the URL to find
           the finalized ServiceBooking.
        3. For users returning to the page: It uses a 'final_service_booking_reference' stored
           in the session.
        4. For pending online payments: If the booking isn't found by payment_intent_id yet
           (due to webhook delay), it displays a "processing" page that polls for completion.
        """
        service_booking = None
        is_processing = False  # Flag to indicate if booking is still being processed by webhook

        # Case 1: Handle in-store payment flow on first arrival
        temp_booking_uuid = request.GET.get('temp_service_booking_uuid')
        if temp_booking_uuid:
            try:
                temp_booking = get_object_or_404(TempServiceBooking, session_uuid=temp_booking_uuid)
                # Convert the temporary booking to a final one. This is the key step for in-store payments.
                service_booking = convert_temp_service_booking(temp_booking.id)
                request.session['final_service_booking_reference'] = service_booking.service_booking_reference
                # Clean up session
                if 'temp_service_booking_uuid' in request.session:
                    del request.session['temp_service_booking_uuid']

                # Redirect to the clean URL to prevent re-processing on refresh
                return redirect('service:service_book_step7')

            except TempServiceBooking.DoesNotExist:
                messages.error(request, "Your booking session has expired. Please start again.")
                return redirect('service:service')
            except Exception as e:
                messages.error(request, f"An error occurred while finalizing your booking: {e}")
                return redirect('service:service')


        # Case 2: Try to retrieve using the final booking reference from the session
        booking_reference = request.session.get('final_service_booking_reference')
        if booking_reference:
            try:
                service_booking = ServiceBooking.objects.get(service_booking_reference=booking_reference)
            except ServiceBooking.DoesNotExist:
                pass  # Silently fail and proceed to next check

        # Case 3: Try to retrieve using payment_intent_id from URL (for online payments)
        payment_intent_id = request.GET.get('payment_intent_id')
        if not service_booking and payment_intent_id:
            try:
                service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
                request.session['final_service_booking_reference'] = service_booking.service_booking_reference
            except ServiceBooking.DoesNotExist:
                is_processing = True # Webhook hasn't processed yet, set flag for client-side polling
            except Exception:
                is_processing = True # Any other error, let polling handle it

        # If after all attempts, no booking is found, handle redirection or processing state
        if not service_booking:
            if is_processing:
                # Render the page with a processing flag for AJAX polling
                context = {
                    'is_processing': True,
                    'payment_intent_id': payment_intent_id,
                }
                return render(request, 'service/step7_confirmation.html', context)
            else:
                # No identifiers found at all, user should not be here
                messages.warning(request, "Could not find a booking confirmation. Please start over if you have not booked.")
                return redirect('service:service')

        # Clean up temporary session data if it still exists
        if 'temp_service_booking_uuid' in request.session:
            del request.session['temp_service_booking_uuid']

        # Prepare context for the confirmed booking
        context = {
            'service_booking': service_booking,
            'booking_status': service_booking.get_booking_status_display(),
            'payment_status': service_booking.get_payment_status_display(),
            'total_amount': service_booking.calculated_total,
            'amount_paid': service_booking.amount_paid,
            'currency': service_booking.currency,
            'motorcycle_details': f"{service_booking.customer_motorcycle.year} {service_booking.customer_motorcycle.brand} {service_booking.customer_motorcycle.model}",
            'customer_name': service_booking.service_profile.name,
            'is_processing': False,
        }
        return render(request, 'service/step7_confirmation.html', context)

