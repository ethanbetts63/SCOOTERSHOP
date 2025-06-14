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
from decimal import Decimal # Ensure Decimal is imported

stripe.api_key = settings.STRIPE_SECRET_KEY

class Step3PaymentView(View):
    def dispatch(self, request, *args, **kwargs):
        print(f"--- Entering Step3PaymentView dispatch method ---")
        print(f"Session data at start: {request.session.keys()}") 
        
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')
        print(f"Retrieved 'temp_sales_booking_uuid' from session: {temp_booking_uuid}")

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid.")
            print('DEBUG: No temp booking uuid found in session for step 3. Redirecting to inventory:used.')
            return redirect('inventory:used')

        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
            request.temp_booking = temp_booking
            print(f"DEBUG: Successfully fetched TempSalesBooking with session_uuid: {temp_booking.session_uuid} (PK: {temp_booking.pk})")
        except Http404:
            messages.error(request, "Your booking session could not be found.")
            print(f"DEBUG: Http404 - TempSalesBooking not found for session_uuid: {temp_booking_uuid}. Redirecting to inventory:used.")
            return redirect('inventory:used')
        except Exception as e:
            messages.error(request, "An unexpected error occurred while retrieving your booking.")
            print(f"ERROR: Exception fetching TempSalesBooking for session_uuid {temp_booking_uuid}: {e}")
            return redirect('inventory:used')


        if not temp_booking.motorcycle:
            messages.error(request, "Please select a motorcycle first.")
            print('DEBUG: Temp booking has no motorcycle. Redirecting to inventory:used.')
            return redirect('inventory:used') 
        
        if not temp_booking.sales_profile:
            messages.error(request, "Please provide your contact details first.")
            print('DEBUG: Temp booking has no sales profile. Redirecting to inventory:step2_booking_details_and_appointment.')
            return redirect('inventory:step2_booking_details_and_appointment') 

        try:
            request.inventory_settings = InventorySettings.objects.get()
            print('DEBUG: Successfully retrieved InventorySettings.')
        except InventorySettings.DoesNotExist:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            print('DEBUG: InventorySettings not found. Redirecting to inventory:used.')
            return redirect('inventory:used')

        if not temp_booking.deposit_required_for_flow:
            messages.warning(request, "Payment is not required for this type of booking. Redirecting to confirmation.")
            redirect_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={temp_booking.stripe_payment_intent_id if temp_booking.stripe_payment_intent_id else ""}'
            print(f'DEBUG: Deposit not required. Redirecting to: {redirect_url}')
            return redirect(redirect_url)

        print(f"--- Exiting Step3PaymentView dispatch method, calling super().dispatch ---")
        return super().dispatch(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        print(f"--- Entering Step3PaymentView GET method ---")
        temp_booking = request.temp_booking
        inventory_settings = request.inventory_settings
        currency = inventory_settings.currency_code
        
        amount_to_pay = temp_booking.amount_paid
        print(f"DEBUG (Step3 GET): TempSalesBooking amount_paid: {amount_to_pay}")

        if amount_to_pay is None or amount_to_pay <= 0:
            messages.error(request, "The amount to pay is invalid. Please review your booking details.")
            print(f"DEBUG (Step3 GET): Amount to pay is invalid ({amount_to_pay}). Redirecting to inventory:step2_booking_details_and_appointment.")
            return redirect('inventory:step2_booking_details_and_appointment')

        sales_customer_profile = temp_booking.sales_profile
        payment_obj = Payment.objects.filter(temp_sales_booking=temp_booking).first()
        print(f"DEBUG (Step3 GET): Existing Payment object: {payment_obj}")

        try:
            intent, payment_obj = create_or_update_sales_payment_intent(
                temp_booking=temp_booking,
                sales_profile=sales_customer_profile,
                amount_to_pay=amount_to_pay,
                currency=currency,
                existing_payment_obj=payment_obj
            )
            print(f"DEBUG (Step3 GET): Stripe Payment Intent created/updated. Intent ID: {intent.id if intent else 'None'}")

        except stripe.error.StripeError as e:
            messages.error(request, f"Payment system error: {e}. Please try again later.")
            print(f"ERROR (Step3 GET): Stripe error: {e}. Redirecting to inventory:step2_booking_details_and_appointment.")
            return redirect('inventory:step2_booking_details_and_appointment')
        except Exception as e:
            messages.error(request, "An unexpected error occurred during payment setup. Please try again.")
            print(f"ERROR (Step3 GET): Unexpected error during payment setup: {e}. Redirecting to inventory:step2_booking_details_and_appointment.")
            return redirect('inventory:step2_booking_details_and_appointment')

        if not intent:
            messages.error(request, "Could not set up payment. Please try again.")
            print(f"DEBUG (Step3 GET): No Stripe Payment Intent returned. Redirecting to inventory:step2_booking_details_and_appointment.")
            return redirect('inventory:step2_booking_details_and_appointment')

        # Calculate amount_remaining here and pass it to the context
        amount_remaining = Decimal('0.00')
        if temp_booking.motorcycle and temp_booking.motorcycle.price is not None:
            amount_remaining = temp_booking.motorcycle.price - amount_to_pay
        print(f"DEBUG (Step3 GET): Calculated amount_remaining: {amount_remaining}")


        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
            'amount_remaining': amount_remaining, # <--- NEW CONTEXT VARIABLE
        }
        print(f"--- Exiting Step3PaymentView GET method, rendering template ---")
        return render(request, 'inventory/step3_payment.html', context)

    def post(self, request, *args, **kwargs):
        print(f"--- Entering Step3PaymentView POST method ---")
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
            print(f"DEBUG (Step3 POST): Received payment_intent_id: {payment_intent_id}")
        except json.JSONDecodeError:
            print("ERROR (Step3 POST): Invalid JSON format in request body.")
            return JsonResponse({'error': 'Invalid JSON format in request body'}, status=400)

        if not payment_intent_id:
            print("DEBUG (Step3 POST): No payment_intent_id received.")
            return JsonResponse({'error': 'Payment Intent ID is required in the request'}, status=400)

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            print(f"DEBUG (Step3 POST): Retrieved Stripe Intent Status: {intent.status}")

            payment_obj = Payment.objects.filter(stripe_payment_intent_id=intent.id).first()

            if intent.status == 'succeeded':
                print("DEBUG (Step3 POST): Payment Intent Succeeded. Redirecting to confirmation.")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    'redirect_url': reverse('inventory:step4_confirmation') + f'?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method', 'processing']:
                print(f"DEBUG (Step3 POST): Payment Intent Status: {intent.status}. Requires further action.")
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                        print(f"DEBUG (Step3 POST): Payment object status updated to {intent.status}.")
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts provided by Stripe.'
                })

            else:
                print(f"DEBUG (Step3 POST): Payment Intent Status: {intent.status}. Payment failed or unexpected.")
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                        print(f"DEBUG (Step3 POST): Payment object status updated to {intent.status}.")
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed or an unexpected status occurred. Please try again.'
                })

        except stripe.error.StripeError as e:
            print(f"ERROR (Step3 POST): Stripe error: {e}.")
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            print(f"ERROR (Step3 POST): An internal server error occurred during payment processing: {e}.")
            return JsonResponse({'error': 'An internal server error occurred during payment processing.'}, status=500)

