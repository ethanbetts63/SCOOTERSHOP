from django.views import View
from django.http import JsonResponse
from service.models import ServiceBooking
from payments.models import Payment


class Step7StatusCheckView(View):
    def get(self, request):
        print("DEBUG: Step7StatusCheckView - GET method entered (AJAX status check).")
        payment_intent_id = request.GET.get('payment_intent_id')
        print(f"DEBUG: Step7StatusCheckView - payment_intent_id from GET param: {payment_intent_id}")

        if not payment_intent_id:
            print("ERROR: Step7StatusCheckView - Payment Intent ID is required.")
            return JsonResponse({'status': 'error', 'message': 'Payment Intent ID is required.'}, status=400)

        try:
            service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
            print(f"DEBUG: Step7StatusCheckView - ServiceBooking found: {service_booking.service_booking_reference}. Status: {service_booking.payment_status}")

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
            request.session['service_booking_reference'] = service_booking.service_booking_reference
            print("DEBUG: Step7StatusCheckView - Returning 'ready' status JSON.")
            return JsonResponse(response_data)

        except ServiceBooking.DoesNotExist:
            print(f"DEBUG: Step7StatusCheckView - ServiceBooking not found for PI ID {payment_intent_id}. Checking Payment object.")
            try:
                Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                print(f"DEBUG: Step7StatusCheckView - Payment object found for PI ID {payment_intent_id}. Returning 'processing' status.")
                return JsonResponse({'status': 'processing', 'message': 'Booking finalization is still in progress.'})
            except Payment.DoesNotExist:
                print(f"ERROR: Step7StatusCheckView - Neither ServiceBooking nor Payment found for PI ID {payment_intent_id}. Returning 'error' status.")
                return JsonResponse({'status': 'error', 'message': 'Booking finalization failed. Please contact support for assistance.'}, status=500)
        except Exception as e:
            print(f"ERROR: Step7StatusCheckView - An internal server error occurred in status check: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)

