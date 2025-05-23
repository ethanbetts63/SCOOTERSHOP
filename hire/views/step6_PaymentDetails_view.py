# hire/views/step6_PaymentDetails_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction # Still useful for GET method's atomic updates
from django.conf import settings
import stripe
import json
import logging

from hire.models import TempHireBooking
from payments.models import Payment

logger = logging.getLogger(__name__)

# Set your Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentDetailsView(View):
    def get(self, request):
        """
        Handles GET requests to display the payment form and create/retrieve Stripe PaymentIntent.
        This method ensures a PaymentIntent exists for the current temporary booking.
        """
        # Step 1: Retrieve temporary booking from session
        temp_booking_id = request.session.get('temp_booking_id')
        logger.debug(f"In Step6PaymentDetailsView GET. temp_booking_id from session: {temp_booking_id}")

        if not temp_booking_id:
            logger.debug("No temp_booking_id in session. Redirecting to step 2.")
            return redirect('hire:step2_choose_bike')

        temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)
        logger.debug(f"Retrieved TempHireBooking: {temp_booking.id}")

        # Step 2: Determine amount and currency based on payment option
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

        # Step 3: Find or create a Payment object and Stripe PaymentIntent
        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()
        intent = None # Initialize intent to None

        if payment_obj and payment_obj.stripe_payment_intent_id:
            try:
                # Retrieve the existing Stripe PaymentIntent
                intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)
                logger.debug(f"Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")

                # If the PaymentIntent has already succeeded, redirect to confirmation.
                # The HireBooking creation is handled by the webhook, so we just redirect.
                if intent.status == 'succeeded':
                    logger.debug(f"Existing Stripe PaymentIntent {intent.id} is already succeeded. Redirecting to confirmation.")
                    # Update the Payment object's status in case it's out of sync
                    if payment_obj.status != 'succeeded':
                        payment_obj.status = 'succeeded'
                        payment_obj.save()
                        logger.debug(f"Updated Payment DB object {payment_obj.id} status to 'succeeded'.")
                    
                    # Clear the temp_booking_id from session as it's now finalized (by webhook)
                    if 'temp_booking_id' in request.session:
                        del request.session['temp_booking_id']
                        logger.debug(f"Cleared temp_booking_id {temp_booking_id} from session.")
                    
                    # Redirect to step 7, passing the payment_intent_id
                    return redirect('hire:step7_confirmation', payment_intent_id=intent.id)

                # Check if the existing PaymentIntent needs modification
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
                            'booking_type': 'hire_booking', # Ensure metadata is consistent on modify
                        }
                    )
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status # Update status after modification
                    payment_obj.description = payment_description
                    payment_obj.save()
                    logger.debug(f"Modified PaymentIntent: {intent.id}, New Amount: {intent.amount}, New Currency: {intent.currency}")
                elif not is_modifiable and intent.status not in ['succeeded', 'canceled', 'failed']:
                    # If it's not modifiable and not succeeded/canceled/failed, something is odd.
                    # Treat as if no valid intent exists and create a new one.
                    logger.debug(f"Existing PaymentIntent {intent.id} is not modifiable ({intent.status}) and not succeeded/canceled/failed. Forcing creation of new one.")
                    payment_obj = None # This will lead to new intent creation below
                    intent = None # Reset intent as it's no longer valid for this flow
                elif intent.status in ['canceled', 'failed']:
                    # If the existing intent is canceled or failed, we need a new one
                    logger.debug(f"Existing PaymentIntent {intent.id} is {intent.status}. Forcing creation of new one.")
                    payment_obj = None # This will lead to new intent creation below
                    intent = None # Reset intent as it's no longer valid for this flow
                else:
                    # If intent exists, is modifiable, and amounts/currencies match, just use it.
                    # Or if it's processing, we still use it.
                    logger.debug(f"Re-using existing PaymentIntent {intent.id} (Status: {intent.status}).")
                    # Ensure local DB status is up-to-date
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error retrieving or modifying existing PaymentIntent ({payment_obj.stripe_payment_intent_id}): {e}. Forcing creation of new one.")
                payment_obj = None # Force creation of new PaymentIntent/Payment object
                intent = None # Reset intent as it's no longer valid

        # If no valid payment_obj or intent exists (either initially or after checks/errors), create a new one.
        if not payment_obj or not intent:
            logger.debug("Creating new Stripe PaymentIntent and Payment DB object.")
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100), # Stripe expects amount in cents
                    currency=currency,
                    metadata={
                        'temp_booking_id': str(temp_booking.id),
                        'user_id': str(request.user.id) if request.user.is_authenticated else 'guest',
                        'booking_type': 'hire_booking', # IMPORTANT: Add this metadata for webhook dispatch
                    },
                    description=payment_description
                )
                logger.debug(f"Created new Stripe PaymentIntent: {intent.id}, Client Secret: {intent.client_secret}, Status: {intent.status}")

                # Create or update the Payment object in your database
                if payment_obj: # If payment_obj existed but was invalidated (e.g., old intent failed/canceled)
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    payment_obj.save()
                    logger.debug(f"Updated existing Payment DB object: {payment_obj.id} with new Stripe Intent.")
                else: # Completely new Payment object
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

        # Ensure intent is not None before passing to context
        if not intent:
            logger.error("PaymentIntent could not be created or retrieved. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        # Step 4: Render the payment page
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
        
        # Step 1: Parse incoming JSON data
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

        # Step 2: Retrieve PaymentIntent from Stripe and update local Payment object
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            logger.debug(f"Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")

            payment_obj = get_object_or_404(Payment, stripe_payment_intent_id=intent.id)
            logger.debug(f"Found Payment DB object: {payment_obj.id}")

            # Update the Payment object's status in your database
            # The actual booking finalization (HireBooking creation, TempBooking deletion)
            # will be triggered by the Stripe webhook (payment_intent.succeeded event).
            if payment_obj.status != intent.status:
                payment_obj.status = intent.status
                payment_obj.save()
                logger.info(f"Updated Payment DB object status to: {payment_obj.status} based on client-side confirmation.")
            else:
                logger.info(f"Payment DB object status already {payment_obj.status}. No update needed.")

            # Step 3: Provide client-side response based on Stripe's status
            if intent.status == 'succeeded':
                logger.info("Client reports Payment Intent succeeded. Awaiting webhook for finalization.")
                # Return a success response to the client.
                # The client-side JS will then redirect to a "processing" or "thank you" page.
                # The final confirmation page will be reached once the webhook processes.
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    # IMPORTANT: Pass payment_intent_id in the redirect URL
                    'redirect_url': f'/hire/book/step7/?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method']:
                logger.info(f"Payment Intent requires further action or is pending: {intent.status}")
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts.',
                    'redirect_url': f'/hire/payment_failed/?payment_intent_id={payment_intent_id}' # Also pass for failed/action
                })

            else:
                logger.warning(f"Payment Intent status is unexpected from client: {intent.status}")
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed or an unexpected status occurred. Please try again.',
                    'redirect_url': f'/hire/payment_failed/?payment_intent_id={payment_intent_id}' # Also pass for failed
                })

        # Step 4: Handle errors during POST processing
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API Error in POST: {e}")
            return JsonResponse({'error': str(e)}, status=500)
        except Payment.DoesNotExist:
            logger.error(f"Payment object not found for Stripe Intent ID: {payment_intent_id} in POST request.")
            return JsonResponse({'error': 'Payment record not found in DB'}, status=404)
        except Exception as e:
            logger.exception(f"An unexpected error occurred in POST for PaymentIntent {payment_intent_id}: {e}")
            return JsonResponse({'error': 'An internal server error occurred'}, status=500)
