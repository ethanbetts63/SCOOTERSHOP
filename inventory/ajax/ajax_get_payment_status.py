from django.views import View
from django.http import JsonResponse
from inventory.models import SalesBooking
from payments.models import Payment


class GetPaymentStatusView(View):
    def get(self, request):
        payment_intent_id = request.GET.get('payment_intent_id')

        if not payment_intent_id:
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required.'}, status=400)

        try:
            sales_booking = SalesBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

            response_data = {
                'status': 'ready',
                'booking_reference': sales_booking.sales_booking_reference,
                'booking_status': sales_booking.get_booking_status_display(),
                'payment_status': sales_booking.get_payment_status_display(),
                'amount_paid': str(sales_booking.amount_paid),
                'currency': sales_booking.currency,
                'motorcycle_details': f"{sales_booking.motorcycle.year} {sales_booking.motorcycle.brand} {sales_booking.motorcycle.model}",
                'customer_name': sales_booking.sales_profile.name,
                # Include appointment details if they exist
                'appointment_date': sales_booking.appointment_date.strftime('%d %b %Y') if sales_booking.appointment_date else None,
                'appointment_time': sales_booking.appointment_time.strftime('%I:%M %p') if sales_booking.appointment_time else None,
            }
            # Set the permanent booking reference in session for direct confirmation page access
            request.session['sales_booking_reference'] = sales_booking.sales_booking_reference

            # Clean up the temporary session UUID if it exists
            if 'temp_sales_booking_uuid' in request.session:
                del request.session['temp_sales_booking_uuid']
                
            return JsonResponse(response_data)

        except SalesBooking.DoesNotExist:
            try:
                # If SalesBooking doesn't exist but Payment does, it's still processing via webhook
                Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                return JsonResponse({'status': 'processing', 'message': 'Booking finalization is still in progress.'})
            except Payment.DoesNotExist:
                # Neither SalesBooking nor Payment found for this intent ID
                return JsonResponse({'status': 'error', 'message': 'Booking finalization failed. Please contact support for assistance.'}, status=500)
        except Exception as e:
            # Catch any other unexpected errors during the status check
            return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)

