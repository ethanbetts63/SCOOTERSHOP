from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, Http404
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from django.contrib import messages

import stripe
import json

from payments.models import Payment
from service.models import TempServiceBooking, ServiceProfile, ServiceSettings, ServiceType
from django.contrib.auth import get_user_model

stripe.api_key = settings.STRIPE_SECRET_KEY

class Step6PaymentView(View):
    def dispatch(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get('temp_service_booking_uuid')

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid.")
            return redirect('service:service')

        try:
            temp_booking = get_object_or_404(TempServiceBooking, session_uuid=temp_booking_uuid)
            request.temp_booking = temp_booking
        except Http404:
            messages.error(request, "Your booking session could not be found.")
            return redirect('service:service')

        if not temp_booking.customer_motorcycle:
            messages.error(request, "Please select or add your motorcycle details first (Step 3).")
            return redirect('service:service_book_step3')
        
        if not temp_booking.service_profile:
            messages.error(request, "Please provide your contact details first (Step 4).")
            return redirect('service:service_book_step4')

        try:
            request.service_settings = ServiceSettings.objects.get()
        except ServiceSettings.DoesNotExist:
            messages.error(request, "Service settings are not configured. Please contact support.")
            return redirect('service:service')

        return super().dispatch(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        temp_booking = request.temp_booking
        service_settings = request.service_settings

        print(f"DEBUG: Step 6 - Retrieved temp_booking.payment_option: {temp_booking.payment_option}")

        payment_option = temp_booking.payment_option
        currency = service_settings.currency_code

        amount_to_pay = None
        if payment_option == 'online_full': # Corrected from 'full_online' to 'online_full' based on TempServiceBooking model
            amount_to_pay = temp_booking.service_type.base_price
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.calculated_deposit_amount
        elif payment_option == 'in_store_full':
            return redirect(reverse('service:service_book_step7') + f'?temp_booking_uuid={temp_booking.session_uuid}')
        else:
            print(f"DEBUG: Step 6 - No valid payment option recognized. payment_option: {payment_option}")
            messages.error(request, "No valid payment option selected. Please choose a payment method.")
            return redirect('service:service_book_step5')
        
        print(f"DEBUG: Step 6 - Payment option: {payment_option}, Amount to pay: {amount_to_pay}")

        if amount_to_pay is None or amount_to_pay <= 0:
            messages.error(request, "The amount to pay is invalid. Please review your booking details.")
            return redirect('service:service_book_step5')

        payment_description = (
            f"Motorcycle service booking for {temp_booking.customer_motorcycle.year} "
            f"{temp_booking.customer_motorcycle.brand} {temp_booking.customer_motorcycle.model} "
            f"({temp_booking.service_type.name})"
        )

        payment_obj = Payment.objects.filter(temp_service_booking=temp_booking).first()
        intent = None

        service_customer_profile = temp_booking.service_profile

        try:
            if payment_obj and payment_obj.stripe_payment_intent_id:
                try:
                    intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)

                    amount_in_cents = int(amount_to_pay * 100)
                    amount_changed = intent.amount != amount_in_cents
                    currency_changed = intent.currency.lower() != currency.lower()
                    
                    is_modifiable_or_in_progress = intent.status in [
                        'requires_payment_method', 'requires_confirmation', 'requires_action',
                        'processing', 'canceled'
                    ]

                    if (amount_changed or currency_changed) and is_modifiable_or_in_progress:
                        intent = stripe.PaymentIntent.modify(
                            payment_obj.stripe_payment_intent_id,
                            amount=amount_in_cents,
                            currency=currency,
                            description=payment_description,
                            metadata={
                                'temp_service_booking_uuid': str(temp_booking.session_uuid),
                                'service_profile_id': str(service_customer_profile.id) if service_customer_profile else 'guest',
                                'booking_type': 'service_booking',
                            }
                        )
                        payment_obj.amount = amount_to_pay
                        payment_obj.currency = currency
                        payment_obj.status = intent.status
                        payment_obj.description = payment_description
                        payment_obj.save()
                    elif intent.status == 'succeeded':
                        context = {
                            'payment_already_succeeded': True,
                            'amount': amount_to_pay,
                            'currency': currency.upper(),
                            'temp_booking': temp_booking,
                            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                        }
                        return render(request, 'service/step6_payment.html', context)
                    elif not is_modifiable_or_in_progress and intent.status not in ['succeeded', 'failed']:
                        intent = None
                    elif intent.status == 'failed':
                        intent = None
                    else:
                        if payment_obj.status != intent.status:
                            payment_obj.status = intent.status
                            payment_obj.save()

                except stripe.error.StripeError as e:
                    intent = None

            if not intent:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100),
                    currency=currency,
                    metadata={
                        'temp_service_booking_uuid': str(temp_booking.session_uuid),
                        'service_profile_id': str(service_customer_profile.id) if service_customer_profile else 'guest',
                        'booking_type': 'service_booking',
                    },
                    description=payment_description
                )

                if payment_obj:
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    if service_customer_profile and not payment_obj.service_customer_profile:
                        payment_obj.service_customer_profile = service_customer_profile
                    payment_obj.save()
                else:
                    payment_obj = Payment.objects.create(
                        temp_service_booking=temp_booking,
                        service_customer_profile=service_customer_profile,
                        stripe_payment_intent_id=intent.id,
                        amount=amount_to_pay,
                        currency=currency,
                        status=intent.status,
                        description=payment_description
                    )

        except stripe.error.StripeError as e:
            messages.error(request, f"Payment system error: {e}. Please try again later.")
            return redirect('service:service_book_step5')
        except Exception as e:
            messages.error(request, "An unexpected error occurred during payment setup. Please try again.")
            return redirect('service:service_book_step5')

        if not intent:
            messages.error(request, "Could not set up payment. Please try again.")
            return redirect('service:service_book_step5')

        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        return render(request, 'service/step6_payment.html', context)

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
                    'redirect_url': reverse('service:service_book_step7') + f'?payment_intent_id={payment_intent_id}'
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
