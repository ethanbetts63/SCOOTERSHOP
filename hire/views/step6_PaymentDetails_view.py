# hire/views/step6_PaymentDetails_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from django.urls import reverse # IMPORT THIS!
import stripe
import json
import logging

from payments.models import Payment
from hire.models import TempHireBooking # Import TempHireBooking here

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentDetailsView(View):
    def get(self, request):
        """
        Handles GET requests to display the payment form and create/retrieve Stripe PaymentIntent.
        """
        temp_booking_id = request.session.get('temp_booking_id')
        logger.debug(f"In Step6PaymentDetailsView GET. temp_booking_id from session: {temp_booking_id}")

        if not temp_booking_id:
            logger.debug("No temp_booking_id in session. Redirecting to step 2.")
            return redirect('hire:step2_choose_bike')

        temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)
        logger.debug(f"Retrieved TempHireBooking: {temp_booking.id}")

        payment_option = temp_booking.payment_option
        logger.debug(f"TempHireBooking payment_option: {payment_option}")

        amount_to_pay = None
        currency = temp_booking.currency if hasattr(temp_booking, 'currency') and temp_booking.currency else 'AUD'
        logger.debug(f"TempHireBooking currency: {currency}")

        if payment_option == 'online_full':
            amount_to_pay = temp_booking.grand_total
            logger.debug(f"Payment option 'online_full'. Amount to pay: {amount_to_pay}")
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.deposit_amount
            logger.debug(f"Payment option 'online_deposit'. Amount to pay: {amount_to_pay}")
        else:
            logger.debug(f"Invalid payment option '{payment_option}'. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        if amount_to_pay is None:
            logger.debug("amount_to_pay is None. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        payment_description = f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"

        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()
        intent = None

        if payment_obj and payment_obj.stripe_payment_intent_id:
            try:
                intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)
                logger.debug(f"Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")

                # Removed: Premature redirect for succeeded PaymentIntent in GET method.
                # This logic will now be handled by the client-side POST after payment confirmation.

                amount_changed = intent.amount != int(amount_to_pay * 100)
                currency_changed = intent.currency.lower() != currency.lower()
                is_modifiable = intent.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']

                if (amount_changed or currency_changed) and is_modifiable:
                    logger.debug(f"Mismatch in amount/currency for modifiable intent. Modifying PaymentIntent {intent.id}.")
                    intent = stripe.PaymentIntent.modify(
                        payment_obj.stripe_payment_intent_id,
                        amount=int(amount_to_pay * 100),
                        currency=currency,
                        description=payment_description,
                        metadata={
                            'temp_booking_id': str(temp_booking.id),
                            'user_id': str(request.user.id) if request.user.is_authenticated else 'guest',
                            'booking_type': 'hire_booking',
                        }
                    )
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    payment_obj.save()
                    logger.debug(f"Modified PaymentIntent: {intent.id}, New Amount: {intent.amount}, New Currency: {intent.currency}")
                elif not is_modifiable and intent.status not in ['succeeded', 'canceled', 'failed']:
                    logger.debug(f"Existing PaymentIntent {intent.id} is not modifiable ({intent.status}) and not succeeded/canceled/failed. Forcing creation of new one.")
                    payment_obj = None
                    intent = None
                elif intent.status in ['canceled', 'failed']:
                    logger.debug(f"Existing PaymentIntent {intent.id} is {intent.status}. Forcing creation of new one.")
                    payment_obj = None
                    intent = None
                else:
                    logger.debug(f"Re-using existing PaymentIntent {intent.id} (Status: {intent.status}).")
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error retrieving or modifying existing PaymentIntent ({payment_obj.stripe_payment_intent_id}): {e}. Forcing creation of new one.")
                payment_obj = None
                intent = None

        if not payment_obj or not intent:
            logger.debug("Creating new Stripe PaymentIntent and Payment DB object.")
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100),
                    currency=currency,
                    metadata={
                        'temp_booking_id': str(temp_booking.id),
                        'user_id': str(request.user.id) if request.user.is_authenticated else 'guest',
                        'booking_type': 'hire_booking',
                    },
                    description=payment_description
                )
                logger.debug(f"Created new Stripe PaymentIntent: {intent.id}, Client Secret: {intent.client_secret}, Status: {intent.status}")

                if payment_obj:
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    payment_obj.save()
                    logger.debug(f"Updated existing Payment DB object: {payment_obj.id} with new Stripe Intent.")
                else:
                    payment_obj = Payment.objects.create(
                        temp_hire_booking=temp_booking,
                        user=request.user if request.user.is_authenticated else None,
                        stripe_payment_intent_id=intent.id,
                        amount=amount_to_pay,
                        currency=currency,
                        status=intent.status,
                        description=payment_description
                    )
                    logger.debug(f"Created new Payment DB object: {payment_obj.id}")
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error creating PaymentIntent: {e}")
                return redirect('hire:step5_summary_payment_options')

        if not intent:
            logger.error("PaymentIntent could not be created or retrieved. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        logger.debug("Rendering step6_payment_details.html with context.")
        return render(request, 'hire/step6_payment_details.html', context)

    def post(self, request):
        """
        Handles POST requests from the client-side after Stripe.js processes the payment.
        This method's primary role is to update the local Payment object status and
        provide immediate feedback to the client.
        The actual booking finalization (creating HireBooking, deleting TempHireBooking)
        is now handled by the Stripe webhook.
        """
        logger.debug("Entering Step6PaymentDetailsView POST method for client-side update.")
        
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
            logger.debug(f"Received payment_intent_id from client: {payment_intent_id}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body.")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not payment_intent_id:
            logger.error("No payment_intent_id provided in POST request.")
            return JsonResponse({'error': 'Payment Intent ID is required'}, status=400)

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            logger.debug(f"Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")

            payment_obj = get_object_or_404(Payment, stripe_payment_intent_id=intent.id)
            logger.debug(f"Found Payment DB object: {payment_obj.id}")

            if payment_obj.status != intent.status:
                payment_obj.status = intent.status
                payment_obj.save()
                logger.info(f"Updated Payment DB object status to: {payment_obj.status} based on client-side confirmation.")
            else:
                logger.info(f"Payment DB object status already {payment_obj.status}. No update needed.")

            if intent.status == 'succeeded':
                logger.info("Client reports Payment Intent succeeded. Awaiting webhook for finalization.")
                # This is the correct place to return the redirect URL to the client.
                # The client-side JS will then perform the actual redirect.
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    'redirect_url': f'/hire/book/step7/?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method']:
                logger.info(f"Payment Intent requires further action or is pending: {intent.status}")
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts.',
                    'redirect_url': f'/hire/payment_failed/?payment_intent_id={payment_intent_id}'
                })

            else:
                logger.warning(f"Payment Intent status is unexpected from client: {intent.status}")
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed or an unexpected status occurred. Please try again.',
                    'redirect_url': f'/hire/payment_failed/?payment_intent_id={payment_intent_id}'
                })

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API Error in POST: {e}")
            return JsonResponse({'error': str(e)}, status=500)
        except Payment.DoesNotExist:
            logger.error(f"Payment object not found for Stripe Intent ID: {payment_intent_id} in POST request.")
            return JsonResponse({'error': 'Payment record not found in DB'}, status=404)
        except Exception as e:
            logger.exception(f"An unexpected error occurred in POST for PaymentIntent {payment_intent_id}: {e}")
            return JsonResponse({'error': 'An internal server error occurred'}, status=500)
