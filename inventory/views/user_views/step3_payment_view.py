from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, Http404
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
import stripe
import json
from payments.models import Payment
from inventory.models import TempSalesBooking, InventorySettings, Motorcycle
from inventory.utils.create_update_sales_payment_intent import create_or_update_sales_payment_intent


stripe.api_key = settings.STRIPE_SECRET_KEY

class Step3PaymentView(View):
    def dispatch(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid.")
            print('No temp booking uuid in step 3')
            return redirect('inventory:used')

        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
            request.temp_booking = temp_booking
        except Http404:
            messages.error(request, "Your booking session could not be found.")
            return redirect('inventory:used')

        if not temp_booking.motorcycle:
            messages.error(request, "Please select a motorcycle first.")
            return redirect('inventory:used') 
        
        if not temp_booking.sales_profile:
            messages.error(request, "Please provide your contact details first.")
            return redirect('inventory:sales_book_step2') 

        try:
            request.inventory_settings = InventorySettings.objects.get()
        except InventorySettings.DoesNotExist:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect('inventory:used')

        if not temp_booking.deposit_required_for_flow:
            messages.warning(request, "Payment is not required for this type of booking. Redirecting to confirmation.")
            return redirect(reverse('inventory:sales_book_step4') + f'?payment_intent_id={temp_booking.stripe_payment_intent_id if temp_booking.stripe_payment_intent_id else ""}')

        return super().dispatch(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        temp_booking = request.temp_booking
        inventory_settings = request.inventory_settings
        currency = inventory_settings.currency_code
        
        amount_to_pay = temp_booking.amount_paid

        if amount_to_pay is None or amount_to_pay <= 0:
            messages.error(request, "The amount to pay is invalid. Please review your booking details.")
            return redirect('inventory:sales_book_step2')

        sales_customer_profile = temp_booking.sales_profile
        payment_obj = Payment.objects.filter(temp_sales_booking=temp_booking).first()

        try:
            intent, payment_obj = create_or_update_sales_payment_intent(
                temp_booking=temp_booking,
                sales_profile=sales_customer_profile,
                amount_to_pay=amount_to_pay,
                currency=currency,
                existing_payment_obj=payment_obj
            )

        except stripe.error.StripeError as e:
            messages.error(request, f"Payment system error: {e}. Please try again later.")
            return redirect('inventory:sales_book_step2')
        except Exception as e:
            messages.error(request, "An unexpected error occurred during payment setup. Please try again.")
            return redirect('inventory:sales_book_step2')

        if not intent:
            messages.error(request, "Could not set up payment. Please try again.")
            return redirect('inventory:sales_book_step2')

        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        return render(request, 'inventory/sales/sales_step3_payment.html', context)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format in request body'}, status=400)

        if not payment_intent_id:
            return JsonResponse({'error': 'Payment Intent ID is required in the request'}, status=400)

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            payment_obj = Payment.objects.filter(stripe_payment_intent_id=intent.id).first()

            if intent.status == 'succeeded':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    'redirect_url': reverse('inventory:sales_book_step4') + f'?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method', 'processing']:
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts provided by Stripe.'
                })

            else:
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed or an unexpected status occurred. Please try again.'
                })

        except stripe.error.StripeError as e:
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'error': 'An internal server error occurred during payment processing.'}, status=500)
