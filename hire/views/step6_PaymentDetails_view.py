# hire/views/step6_PaymentDetails_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from django.urls import reverse
import stripe
import json
import logging

from payments.models import Payment
from hire.models import TempHireBooking
from django.contrib.auth import get_user_model # Import get_user_model

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentDetailsView(View):
    def get(self, request):
        """
        Handles GET requests to display the payment form and create/retrieve Stripe PaymentIntent.
        """
        print("DEBUG: Entering PaymentDetailsView GET method.") # Debug print
        logger.debug("In Step6PaymentDetailsView GET. Starting process.")

        temp_booking_id = request.session.get('temp_booking_id')
        logger.debug(f"In Step6PaymentDetailsView GET. temp_booking_id from session: {temp_booking_id}")
        print(f"DEBUG: GET Request - temp_booking_id: {temp_booking_id}") # Debug print

        if not temp_booking_id:
            logger.debug("No temp_booking_id in session. Redirecting to step 2.")
            print("DEBUG: No temp_booking_id. Redirecting to step 2.") # Debug print
            return redirect('hire:step2_choose_bike')

        temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)
        logger.debug(f"Retrieved TempHireBooking: {temp_booking.id}")
        print(f"DEBUG: Retrieved TempHireBooking ID: {temp_booking.id}") # Debug print

        payment_option = temp_booking.payment_option
        logger.debug(f"TempHireBooking payment_option: {payment_option}")
        print(f"DEBUG: Payment option: {payment_option}") # Debug print

        amount_to_pay = None
        currency = temp_booking.currency if hasattr(temp_booking, 'currency') and temp_booking.currency else 'AUD'
        logger.debug(f"TempHireBooking currency: {currency}")
        print(f"DEBUG: Currency: {currency}") # Debug print

        if payment_option == 'online_full':
            amount_to_pay = temp_booking.grand_total
            logger.debug(f"Payment option 'online_full'. Amount to pay: {amount_to_pay}")
            print(f"DEBUG: Amount for 'online_full': {amount_to_pay}") # Debug print
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.deposit_amount
            logger.debug(f"Payment option 'online_deposit'. Amount to pay: {amount_to_pay}")
            print(f"DEBUG: Amount for 'online_deposit': {amount_to_pay}") # Debug print
        else:
            logger.debug(f"Invalid payment option '{payment_option}'. Redirecting to step 5.")
            print(f"DEBUG: Invalid payment option '{payment_option}'. Redirecting to step 5.") # Debug print
            return redirect('hire:step5_summary_payment_options')

        if amount_to_pay is None:
            logger.debug("amount_to_pay is None. Redirecting to step 5.")
            print("DEBUG: Amount to pay is None. Redirecting to step 5.") # Debug print
            return redirect('hire:step5_summary_payment_options')

        payment_description = f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"

        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()
        intent = None

        # --- START: Added logging for user check ---
        if request.user.is_authenticated:
            logger.debug(f"Authenticated user ID: {request.user.id}")
            print(f"DEBUG: User is authenticated. User ID: {request.user.id}") # Debug print
            User = get_user_model()
            try:
                db_user = User.objects.get(id=request.user.id)
                logger.debug(f"User {request.user.id} successfully retrieved from DB.")
                print(f"DEBUG: User {request.user.id} found in DB.") # Debug print
            except User.DoesNotExist:
                logger.error(f"CRITICAL ERROR: Authenticated user {request.user.id} DOES NOT EXIST in the database!")
                print(f"DEBUG: CRITICAL ERROR - Authenticated user {request.user.id} NOT found in DB.") # Debug print
            except Exception as e:
                logger.error(f"Error checking user {request.user.id} in DB: {e}")
                print(f"DEBUG: Error checking user {request.user.id} in DB: {e}") # Debug print
        else:
            logger.debug("User is anonymous (not authenticated).")
            print("DEBUG: User is anonymous.") # Debug print
        # --- END: Added logging for user check ---

        if payment_obj and payment_obj.stripe_payment_intent_id:
            print(f"DEBUG: Found existing payment_obj with Stripe Intent ID: {payment_obj.stripe_payment_intent_id}") # Debug print
            try:
                intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)
                logger.debug(f"Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")
                print(f"DEBUG: Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}") # Debug print

                amount_changed = intent.amount != int(amount_to_pay * 100)
                currency_changed = intent.currency.lower() != currency.lower()
                is_modifiable = intent.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']

                if (amount_changed or currency_changed) and is_modifiable:
                    logger.debug(f"Mismatch in amount/currency for modifiable intent. Modifying PaymentIntent {intent.id}.")
                    print(f"DEBUG: Modifying PaymentIntent {intent.id} due to mismatch.") # Debug print
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
                    print(f"DEBUG: Modified PaymentIntent {intent.id}. New status: {intent.status}") # Debug print
                elif not is_modifiable and intent.status not in ['succeeded', 'canceled', 'failed']:
                    logger.debug(f"Existing PaymentIntent {intent.id} is not modifiable ({intent.status}) and not succeeded/canceled/failed. Forcing creation of new one.")
                    print(f"DEBUG: Existing PI {intent.id} not modifiable. Forcing new PI.") # Debug print
                    payment_obj = None
                    intent = None
                elif intent.status in ['canceled', 'failed']:
                    logger.debug(f"Existing PaymentIntent {intent.id} is {intent.status}. Forcing creation of new one.")
                    print(f"DEBUG: Existing PI {intent.id} is {intent.status}. Forcing new PI.") # Debug print
                    payment_obj = None
                    intent = None
                else:
                    logger.debug(f"Re-using existing PaymentIntent {intent.id} (Status: {intent.status}).")
                    print(f"DEBUG: Re-using existing PI {intent.id}. Status: {intent.status}") # Debug print
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error retrieving or modifying existing PaymentIntent ({payment_obj.stripe_payment_intent_id}): {e}. Forcing creation of new one.")
                print(f"DEBUG: Stripe error with existing PI: {e}. Forcing new PI.") # Debug print
                payment_obj = None
                intent = None

        if not payment_obj or not intent:
            logger.debug("Creating new Stripe PaymentIntent and Payment DB object.")
            print("DEBUG: Creating new Stripe PaymentIntent and Payment DB object.") # Debug print
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
                print(f"DEBUG: Created new Stripe PI: {intent.id}, Status: {intent.status}") # Debug print

                if payment_obj:
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    payment_obj.save()
                    logger.debug(f"Updated existing Payment DB object: {payment_obj.id} with new Stripe Intent.")
                    print(f"DEBUG: Updated existing Payment DB object {payment_obj.id}.") # Debug print
                else:
                    payment_obj = Payment.objects.create(
                        temp_hire_booking=temp_booking,
                        user=request.user if request.user.is_authenticated else None, # This line remains the same
                        stripe_payment_intent_id=intent.id,
                        amount=amount_to_pay,
                        currency=currency,
                        status=intent.status,
                        description=payment_description
                    )
                    logger.debug(f"Created new Payment DB object: {payment_obj.id}")
                    print(f"DEBUG: Created new Payment DB object {payment_obj.id}.") # Debug print
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error creating PaymentIntent: {e}")
                print(f"DEBUG: Stripe error creating PI: {e}. Redirecting.") # Debug print
                return redirect('hire:step5_summary_payment_options')

        if not intent:
            logger.error("PaymentIntent could not be created or retrieved. Redirecting to step 5.")
            print("DEBUG: PaymentIntent not created/retrieved. Redirecting to step 5.") # Debug print
            return redirect('hire:step5_summary_payment_options')

        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        logger.debug("Rendering step6_payment_details.html with context.")
        print("DEBUG: Rendering step6_payment_details.html") # Debug print
        return render(request, 'hire/step6_payment_details.html', context)

    def post(self, request):
        """
        Handles POST requests from the client-side after Stripe.js processes the payment.
        This method's primary role is to update the local Payment object status and
        provide immediate feedback to the client.
        The actual booking finalization (creating HireBooking, deleting TempHireBooking)
        is now handled by the Stripe webhook.
        """
        print("DEBUG: Entering PaymentDetailsView POST method.") # Debug print
        logger.debug("Entering Step6PaymentDetailsView POST method for client-side update.")
        
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
            logger.debug(f"Received payment_intent_id from client: {payment_intent_id}")
            print(f"DEBUG: POST Request - Received payment_intent_id: {payment_intent_id}") # Debug print
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body.")
            print("DEBUG: POST Request - Invalid JSON.") # Debug print
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not payment_intent_id:
            logger.error("No payment_intent_id provided in POST request.")
            print("DEBUG: POST Request - No payment_intent_id.") # Debug print
            return JsonResponse({'error': 'Payment Intent ID is required'}, status=400)

        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            logger.debug(f"Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")
            print(f"DEBUG: POST Request - Retrieved Stripe PI: {intent.id}, Status: {intent.status}") # Debug print

            # Try to get the Payment object. It might have been deleted by the webhook already.
            payment_obj = Payment.objects.filter(stripe_payment_intent_id=intent.id).first()
            print(f"DEBUG: POST Request - Payment object found: {payment_obj.id if payment_obj else 'None'}") # Debug print

            if intent.status == 'succeeded':
                print("DEBUG: POST Request - Payment Intent status: succeeded.") # Debug print
                if payment_obj:
                    # If payment_obj still exists, update its status if necessary
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                        logger.info(f"Updated Payment DB object status to: {payment_obj.status} based on client-side confirmation.")
                        print(f"DEBUG: POST Request - Updated Payment DB object {payment_obj.id} status to succeeded.") # Debug print
                    else:
                        logger.info(f"Payment DB object status already {payment_obj.status}. No update needed.")
                        print(f"DEBUG: POST Request - Payment DB object {payment_obj.id} already succeeded.") # Debug print
                else:
                    # This means the webhook has already processed and deleted the TempHireBooking and Payment.
                    logger.info(f"Payment object for intent ID {payment_intent_id} not found in DB. Assuming webhook processed it.")
                    print(f"DEBUG: POST Request - Payment object for {payment_intent_id} not found. Webhook likely processed.") # Debug print
                
                # In either case (found or not found), if Stripe reports succeeded, redirect to step 7
                logger.info("Client reports Payment Intent succeeded. Redirecting to Step 7 (awaiting webhook for finalization if not already done).")
                print(f"DEBUG: POST Request - Redirecting to step 7 for PI: {payment_intent_id}") # Debug print
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    'redirect_url': f'/hire/book/step7/?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method']:
                print(f"DEBUG: POST Request - Payment Intent requires action: {intent.status}") # Debug print
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                logger.info(f"Payment Intent requires further action or is pending: {intent.status}")
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts.',
                    'redirect_url': f'/hire/payment_failed/?payment_intent_id={payment_intent_id}'
                })

            else:
                print(f"DEBUG: POST Request - Payment Intent unexpected status: {intent.status}") # Debug print
                if payment_obj:
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                logger.warning(f"Payment Intent status is unexpected from client: {intent.status}")
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed or an unexpected status occurred. Please try again.',
                    'redirect_url': f'/hire/payment_failed/?payment_intent_id={payment_intent_id}'
                })

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API Error in POST: {e}")
            print(f"DEBUG: POST Request - Stripe API Error: {e}") # Debug print
            # If Stripe API fails to retrieve the intent, it's a serious issue.
            # We can't confirm the status, so we should return an error.
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            logger.exception(f"An unexpected error occurred in POST for PaymentIntent {payment_intent_id}: {e}")
            print(f"DEBUG: POST Request - Unexpected error: {e}") # Debug print
            return JsonResponse({'error': 'An internal server error occurred'}, status=500)
