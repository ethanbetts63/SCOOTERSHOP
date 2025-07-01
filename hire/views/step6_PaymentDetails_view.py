from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, Http404
from django.db import transaction
from django.conf import settings
from django.urls import reverse
import stripe
import json

from payments.models import Payment
from hire.models import TempHireBooking, DriverProfile
from django.contrib.auth import get_user_model

stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentDetailsView(View):
    def get(self, request):
        temp_booking_id = request.session.get('temp_booking_id')

        if not temp_booking_id:
            return redirect('hire:step2_choose_bike')

        try:
            temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)
        except Http404:
            return redirect('hire:step2_choose_bike')

        payment_option = temp_booking.payment_option
        currency = temp_booking.currency if hasattr(temp_booking, 'currency') and temp_booking.currency else 'AUD'

        amount_to_pay = None
        if payment_option == 'online_full':
            amount_to_pay = temp_booking.grand_total
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.deposit_amount
        else:
            return redirect('hire:step5_summary_payment_options')

        if amount_to_pay is None:
            return redirect('hire:step5_summary_payment_options')

        payment_description = f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"

        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()
        intent = None

        driver_profile = None
        if request.user.is_authenticated:
            User = get_user_model()
            try:
                db_user = User.objects.get(id=request.user.id)
                driver_profile, created = DriverProfile.objects.get_or_create(user=db_user)
            except User.DoesNotExist:
                pass                                                           
            except Exception as e:
                pass                          
        else:
            pass

        try:
            if payment_obj and payment_obj.stripe_payment_intent_id:
                try:
                    intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)

                    amount_changed = intent.amount != int(amount_to_pay * 100)
                    currency_changed = intent.currency.lower() != currency.lower()
                    is_modifiable = intent.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']

                    if (amount_changed or currency_changed) and is_modifiable:
                        intent = stripe.PaymentIntent.modify(
                            payment_obj.stripe_payment_intent_id,
                            amount=int(amount_to_pay * 100),
                            currency=currency,
                            description=payment_description,
                            metadata={
                                'temp_booking_id': str(temp_booking.id),
                                'user_id': str(driver_profile.id) if driver_profile else 'guest',
                                'booking_type': 'hire_booking',
                            }
                        )
                        payment_obj.amount = amount_to_pay
                        payment_obj.currency = currency
                        payment_obj.status = intent.status
                        payment_obj.description = payment_description
                        payment_obj.save()
                    elif not is_modifiable and intent.status not in ['succeeded', 'canceled', 'failed']:
                        intent = None
                    elif intent.status in ['canceled', 'failed']:
                        intent = None
                    elif intent.status == 'succeeded':
                        context = {
                            'payment_already_succeeded': True,
                            'amount': amount_to_pay,
                            'currency': currency.upper(),
                            'temp_booking': temp_booking,
                            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                        }
                        return render(request, 'hire/step6_payment_details.html', context)
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
                        'temp_booking_id': str(temp_booking.id),
                        'user_id': str(driver_profile.id) if driver_profile else 'guest',
                        'booking_type': 'hire_booking',
                    },
                    description=payment_description
                )

                if payment_obj:
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    if driver_profile and not payment_obj.driver_profile:
                        payment_obj.driver_profile = driver_profile
                    payment_obj.save()
                else:
                    payment_obj = Payment.objects.create(
                        temp_hire_booking=temp_booking,
                        driver_profile=driver_profile,
                        stripe_payment_intent_id=intent.id,
                        amount=amount_to_pay,
                        currency=currency,
                        status=intent.status,
                        description=payment_description
                    )

        except stripe.error.StripeError as e:
            return redirect('hire:step5_summary_payment_options')
        except Exception as e:
            return redirect('hire:step5_summary_payment_options')

        if not intent:
            return redirect('hire:step5_summary_payment_options')

        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        return render(request, 'hire/step6_payment_details.html', context)
    def post(self, request):
        """
        Handles POST requests from the client-side after Stripe.js processes the payment.
        This method's primary role is to update the local Payment object status and
        provide immediate feedback to the client.
        The actual booking finalization (creating HireBooking, deleting TempHireBooking)
        is now handled by the Stripe webhook.
        """

        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not payment_intent_id:
            return JsonResponse({'error': 'Payment Intent ID is required'}, status=400)

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            payment_obj = Payment.objects.filter(stripe_payment_intent_id=intent.id).first()

            if intent.status == 'succeeded':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    'redirect_url': f'/hire/book/step7/?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method']:
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts.'
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
            return JsonResponse({'error': 'An internal server error occurred'}, status=500)