from django.views import View
from django.http import JsonResponse
from service.models import ServiceBooking
from payments.models import Payment


class Step7StatusCheckView(View):
    def get(self, request):
        payment_intent_id = request.GET.get('payment_intent_id')

        if not payment_intent_id:
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required.'}, status=400)

        try:
            service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)

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
            request.session['final_service_booking_reference'] = service_booking.service_booking_reference
            return JsonResponse(response_data)

        except ServiceBooking.DoesNotExist:
            try:
                Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                return JsonResponse({'status': 'processing', 'message': 'Booking finalization is still in progress.'})
            except Payment.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Booking finalization failed. Please contact support for assistance.'}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)

