from django.views import View
from django.http import JsonResponse
from service.models import ServiceBooking
from payments.models import Payment


class Step7StatusCheckView(View):
    """
    AJAX endpoint for the confirmation page to poll for the booking status
    when an online payment is being processed asynchronously by the Stripe webhook.
    """
    def get(self, request):
        """
        Checks the status of a ServiceBooking based on a payment_intent_id.
        Returns JSON indicating if the booking is 'ready' or still 'processing'.
        """
        payment_intent_id = request.GET.get('payment_intent_id')

        if not payment_intent_id:
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required.'}, status=400)

        try:
            # Try to find the final ServiceBooking via the payment intent ID
            service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

            # If found, the webhook has run successfully. Return the booking details.
            response_data = {
                'status': 'ready',
                'booking_reference': service_booking.service_booking_reference,
                'booking_status': service_booking.get_booking_status_display(),
                'payment_status': service_booking.get_payment_status_display(),
                'total_amount': str(service_booking.calculated_total),
                'amount_paid': str(service_booking.amount_paid),
                'currency': service_booking.currency,
                'service_type': service_booking.service_type.name,
                'service_date': service_booking.service_date.strftime('%d %b %Y'),
                'dropoff_datetime': f"{service_booking.dropoff_date.strftime('%d %b %Y')} at {service_booking.dropoff_time.strftime('%I:%M %p')}",
                'motorcycle_details': f"{service_booking.customer_motorcycle.year} {service_booking.customer_motorcycle.brand} {service_booking.customer_motorcycle.model}",
                'customer_name': service_booking.service_profile.name,
            }
            # Store the final reference in the session once confirmed via polling
            request.session['final_service_booking_reference'] = service_booking.service_booking_reference
            return JsonResponse(response_data)

        except ServiceBooking.DoesNotExist:
            # Booking not found. Check if the underlying Payment object exists to determine status.
            try:
                Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                # If Payment exists but ServiceBooking doesn't, it's still processing.
                return JsonResponse({'status': 'processing', 'message': 'Booking finalization is still in progress.'})
            except Payment.DoesNotExist:
                # If neither object exists, something went wrong in the webhook.
                return JsonResponse({'status': 'error', 'message': 'Booking finalization failed. Please contact support for assistance.'}, status=500)
        except Exception as e:
            # Catch any other unexpected errors.
            return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)
