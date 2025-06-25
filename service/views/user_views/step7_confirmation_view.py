from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from service.models import ServiceBooking
from payments.models import Payment
from service.utils.booking_protection import set_recent_booking_flag # NEW: Import the utility

class Step7ConfirmationView(View):
    def get(self, request):
        service_booking = None
        is_processing = False

        booking_reference = request.session.get('service_booking_reference')
        if booking_reference:
            try:
                service_booking = ServiceBooking.objects.get(service_booking_reference=booking_reference)
            except ServiceBooking.DoesNotExist:
                del request.session['service_booking_reference']
                pass # Continue to check payment_intent_id

        payment_intent_id = request.GET.get('payment_intent_id')
        if not service_booking and payment_intent_id:
            try:
                service_booking = ServiceBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
                request.session['service_booking_reference'] = service_booking.service_booking_reference
                is_processing = False

            except ServiceBooking.DoesNotExist:
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                   
                except Payment.DoesNotExist:
                    is_processing = False
            except Exception as e:
                try:
                    Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                    is_processing = True
                except Payment.DoesNotExist:
                    is_processing = False


        if service_booking:
            if 'temp_service_booking_uuid' in request.session:
                del request.session['temp_service_booking_uuid']
            
            set_recent_booking_flag(request)

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

        elif is_processing and payment_intent_id:
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'service/step7_confirmation.html', context)
        else:
            messages.warning(request, "Could not find a booking confirmation. Please start over if you have not booked.")
            return redirect('service:service')
