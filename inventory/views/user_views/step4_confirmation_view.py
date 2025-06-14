from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from decimal import Decimal
from inventory.models import SalesBooking
from payments.models import Payment

class Step4ConfirmationView(View):
    def get(self, request):
        sales_booking = None
        is_processing = False

        booking_reference = request.session.get('current_sales_booking_reference')
        if booking_reference:
            try:
                sales_booking = SalesBooking.objects.get(sales_booking_reference=booking_reference)
            except SalesBooking.DoesNotExist:
                del request.session['current_sales_booking_reference']
                pass

        payment_intent_id = request.GET.get('payment_intent_id')
        if not sales_booking and payment_intent_id:
            try:
                sales_booking = SalesBooking.objects.get(stripe_payment_intent_id=payment_intent_id)
                request.session['current_sales_booking_reference'] = sales_booking.sales_booking_reference
                is_processing = False

            except SalesBooking.DoesNotExist:
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


        if sales_booking:
            if 'temp_sales_booking_uuid' in request.session:
                del request.session['temp_sales_booking_uuid']

            amount_owing = Decimal('0.00')
            if sales_booking.motorcycle and sales_booking.motorcycle.price is not None:
                amount_owing = sales_booking.motorcycle.price - sales_booking.amount_paid
            
            if amount_owing < Decimal('0.00'):
                amount_owing = Decimal('0.00')

            context = {
                'sales_booking': sales_booking,
                'booking_status': sales_booking.get_booking_status_display(),
                'payment_status': sales_booking.get_payment_status_display(),
                'amount_paid': sales_booking.amount_paid,
                'currency': sales_booking.currency,
                'motorcycle_details': f"{sales_booking.motorcycle.year} {sales_booking.motorcycle.brand} {sales_booking.motorcycle.model}",
                'customer_name': sales_booking.sales_profile.name,
                'is_processing': False,
                'motorcycle_price': sales_booking.motorcycle.price,
                'amount_owing': amount_owing,
            }
            return render(request, 'inventory/step4_confirmation.html', context)

        elif is_processing and payment_intent_id:
            context = {
                'is_processing': True,
                'payment_intent_id': payment_intent_id,
            }
            return render(request, 'inventory/step4_confirmation.html', context)
        else:
            messages.warning(request, "Could not find a booking confirmation. Please start over if you have not booked.")
            return redirect('inventory:used')
