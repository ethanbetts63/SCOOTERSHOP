from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from service.models import ServiceBooking
from payments.models import Payment

class Step7ConfirmationView(View):
    def get(self, request):
        print("DEBUG: Step7ConfirmationView - GET method entered.")
        service_booking = None
        is_processing = False

        booking_reference = request.session.get('service_booking_reference')
        print(f"DEBUG: Step7ConfirmationView - Session booking_reference: {booking_reference}")

        if booking_reference:
            try:
                service_booking = ServiceBooking.objects.get(service_booking_reference=booking_reference)
                print(f"DEBUG: Step7ConfirmationView - ServiceBooking found by session reference: {service_booking.service_booking_reference}")
            except ServiceBooking.DoesNotExist:
                print(f"DEBUG: Step7ConfirmationView - ServiceBooking not found by session reference: {booking_reference}. Removing from session.")
                del request.session['service_booking_reference']
                pass # Continue to check payment_intent_id

        payment_intent_id = request.GET.get('payment_intent_id')
        print(f"DEBUG: Step7ConfirmationView - payment_intent_id from GET param: {payment_intent_id}")

        if not service_booking and payment_intent_id:
            try:
                service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
                request.session['service_booking_reference'] = service_booking.service_booking_reference
                is_processing = False
                print(f"DEBUG: Step7ConfirmationView - ServiceBooking found by payment_intent_id: {service_booking.service_booking_reference}")

            except ServiceBooking.DoesNotExist:
                print(f"DEBUG: Step7ConfirmationView - ServiceBooking not found by payment_intent_id: {payment_intent_id}. Checking Payment object.")
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                    print(f"DEBUG: Step7ConfirmationView - Payment object found for {payment_intent_id}, setting is_processing=True.")
                except Payment.DoesNotExist:
                    is_processing = False
                    print(f"DEBUG: Step7ConfirmationView - No Payment object found for {payment_intent_id}. is_processing=False.")
            except Exception as e:
                print(f"ERROR: Step7ConfirmationView - Unexpected error when looking up ServiceBooking by payment_intent_id: {e}")
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                except Payment.DoesNotExist:
                    is_processing = False


        if service_booking:
            if 'temp_service_booking_uuid' in request.session:
                print(f"DEBUG: Step7ConfirmationView - Removing temp_service_booking_uuid from session.")
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
                'is_processing': False,
            }
            print(f"DEBUG: Step7ConfirmationView - Rendering confirmation. Booking Ref: {service_booking.service_booking_reference}, Payment Status: {service_booking.payment_status}")
            return render(request, 'service/step7_confirmation.html', context)

        elif is_processing and payment_intent_id:
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            print(f"DEBUG: Step7ConfirmationView - Rendering processing state for Payment Intent: {payment_intent_id}")
            return render(request, 'service/step7_confirmation.html', context)
        else:
            messages.warning(request, "Could not find a booking confirmation. Please start over if you have not booked.")
            print("DEBUG: Step7ConfirmationView - No booking or processing payment intent found. Redirecting to service homepage.")
            return redirect('service:service')

