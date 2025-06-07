from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, Http404
from django.db import transaction
from django.conf import settings
from django.urls import reverse
import stripe
import json

# Import necessary models
from payments.models import Payment
from service.models import TempServiceBooking, ServiceProfile, ServiceSettings, ServiceType
from django.contrib.auth import get_user_model

# Set Stripe API key from Django settings
stripe.api_key = settings.STRIPE_SECRET_KEY

class Step6PaymentView(View):
    """
    Handles Step 6 of the service booking process: Payment Details.
    This view manages the creation and updating of Stripe PaymentIntents
    and local Payment records for service bookings. It interacts with Stripe
    to handle online payments (full or deposit).
    """

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to display the payment details page.
        It retrieves the temporary service booking, calculates the amount due,
        creates or modifies a Stripe PaymentIntent, and passes necessary
        Stripe client-side keys to the template.
        """
        # Retrieve the temporary service booking UUID from the session
        temp_booking_uuid = request.session.get('temp_service_booking_uuid')

        # If no UUID is found, redirect to the first step of the service booking process
        if not temp_booking_uuid:
            return redirect('service:service')

        try:
            # Fetch the temporary service booking object
            temp_booking = get_object_or_404(TempServiceBooking, session_uuid=temp_booking_uuid)
        except Http404:
            # If the temporary booking does not exist, redirect to the first step
            return redirect('service:service')

        # Ensure critical prior steps are completed before proceeding to payment
        # Check if a customer motorcycle has been selected/added
        if not temp_booking.customer_motorcycle:
            # If not, redirect back to the motorcycle details step
            return redirect('service:service_book_step3')
        
        # Check if a service profile (customer details) has been set
        if not temp_booking.service_profile:
            # If not, redirect back to the customer details step
            return redirect('service:service_book_step4')

        # Retrieve site-wide service settings
        try:
            service_settings = ServiceSettings.objects.get()
        except ServiceSettings.DoesNotExist:
            # If settings are not configured, redirect to a safe page or show error
            return redirect('service:service') # Or a more appropriate error page/message

        # Determine the payment option and amount to pay based on the temporary booking
        payment_option = temp_booking.payment_option
        currency = service_settings.currency_code # Use currency from ServiceSettings

        amount_to_pay = None
        if payment_option == 'online_full':
            # For full online payment, use the base_price of the selected service type
            amount_to_pay = temp_booking.service_type.base_price
        elif payment_option == 'online_deposit':
            # For online deposit, use the calculated deposit amount from temp booking
            amount_to_pay = temp_booking.calculated_deposit_amount
        elif payment_option == 'in_store_full':
            # If payment is in-store, no Stripe interaction is needed, redirect to confirmation
            return redirect(reverse('service:service_book_step7') + f'?temp_booking_uuid={temp_booking.session_uuid}')
        else:
            # If no valid payment option is set, redirect back to step 5
            return redirect('service:service_book_step5')

        # If for some reason amount_to_pay is still None, redirect back to step 5
        if amount_to_pay is None or amount_to_pay <= 0:
            return redirect('service:service_book_step5')

        # Create a descriptive string for the Stripe payment intent
        payment_description = (
            f"Motorcycle service booking for {temp_booking.customer_motorcycle.year} "
            f"{temp_booking.customer_motorcycle.brand} {temp_booking.customer_motorcycle.model} "
            f"({temp_booking.service_type.name})"
        )

        # Attempt to find an existing Payment object linked to this temporary booking
        payment_obj = Payment.objects.filter(temp_service_booking=temp_booking).first()
        intent = None # Initialize intent to None

        # Identify the service customer profile (for Stripe metadata and linking Payment object)
        service_customer_profile = temp_booking.service_profile # This should be set in step 4

        try:
            # If a payment object exists and has a Stripe Payment Intent ID
            if payment_obj and payment_obj.stripe_payment_intent_id:
                try:
                    # Retrieve the existing Payment Intent from Stripe
                    intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)

                    # Check if amount or currency has changed or if intent status requires modification
                    amount_changed = intent.amount != int(amount_to_pay * 100)
                    currency_changed = intent.currency.lower() != currency.lower()
                    is_modifiable = intent.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']

                    # If changes detected and intent is modifiable, update it on Stripe
                    if (amount_changed or currency_changed) and is_modifiable:
                        intent = stripe.PaymentIntent.modify(
                            payment_obj.stripe_payment_intent_id,
                            amount=int(amount_to_pay * 100),
                            currency=currency,
                            description=payment_description,
                            metadata={
                                'temp_booking_uuid': str(temp_booking.session_uuid),
                                'service_profile_id': str(service_customer_profile.id) if service_customer_profile else 'guest',
                                'booking_type': 'service_booking', # Mark as service booking
                            }
                        )
                        # Update the local Payment object with modified details
                        payment_obj.amount = amount_to_pay
                        payment_obj.currency = currency
                        payment_obj.status = intent.status
                        payment_obj.description = payment_description
                        payment_obj.save()
                    # If not modifiable and not yet succeeded/canceled/failed, invalidate intent to recreate
                    elif not is_modifiable and intent.status not in ['succeeded', 'canceled', 'failed']:
                        intent = None
                    # If intent is already canceled or failed, invalidate to recreate
                    elif intent.status in ['canceled', 'failed']:
                        intent = None
                    # If intent has already succeeded, redirect to step 7 (confirmation)
                    elif intent.status == 'succeeded':
                        context = {
                            'payment_already_succeeded': True,
                            'amount': amount_to_pay,
                            'currency': currency.upper(),
                            'temp_booking': temp_booking,
                            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                        }
                        return render(request, 'service/step6_payment.html', context)
                    # If status is the same and no modification, just update local status if different
                    else:
                        if payment_obj.status != intent.status:
                            payment_obj.status = intent.status
                            payment_obj.save()

                except stripe.error.StripeError as e:
                    # If retrieving or modifying fails, set intent to None to force recreation
                    intent = None

            # If no existing valid intent or modification failed, create a new one
            if not intent:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100), # Amount in cents
                    currency=currency,
                    metadata={
                        'temp_booking_uuid': str(temp_booking.session_uuid),
                        'service_profile_id': str(service_customer_profile.id) if service_customer_profile else 'guest',
                        'booking_type': 'service_booking', # Mark as service booking
                    },
                    description=payment_description
                )

                # Create or update the local Payment object
                if payment_obj:
                    # Update existing payment object
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    if service_customer_profile and not payment_obj.service_customer_profile:
                        payment_obj.service_customer_profile = service_customer_profile
                    payment_obj.save()
                else:
                    # Create a new payment object
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
            # Handle Stripe API errors during intent creation/modification
            print(f"Stripe Error in GET: {e}") # Log the error
            # Redirect to the previous step with an error indication if possible
            return redirect('service:service_book_step5')
        except Exception as e:
            # Handle any other unexpected errors
            print(f"General Error in GET: {e}") # Log the error
            return redirect('service:service_book_step5')

        # If no intent was successfully created or retrieved, redirect
        if not intent:
            return redirect('service:service_book_step5')

        # Prepare context for rendering the HTML template
        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        return render(request, 'service/step6_payment.html', context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests from the client-side after Stripe.js processes the payment.
        This method's primary role is to update the local Payment object status and
        provide immediate feedback to the client.
        The actual booking finalization (creating ServiceBooking, deleting TempServiceBooking)
        is now handled by the Stripe webhook.
        """
        try:
            # Parse the JSON body of the request
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format in request body'}, status=400)

        # Ensure payment_intent_id is provided
        if not payment_intent_id:
            return JsonResponse({'error': 'Payment Intent ID is required in the request'}, status=400)

        try:
            # Retrieve the Payment Intent from Stripe using the provided ID
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Find the local Payment object associated with this Stripe Payment Intent
            payment_obj = Payment.objects.filter(stripe_payment_intent_id=intent.id).first()

            # Respond based on the Stripe Payment Intent's status
            if intent.status == 'succeeded':
                # Payment succeeded, inform the client to redirect to the confirmation page
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment processed successfully. Your booking is being finalized.',
                    'redirect_url': reverse('service:service_book_step7') + f'?payment_intent_id={payment_intent_id}'
                })

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method']:
                # Payment requires further action from the user or is pending
                if payment_obj:
                    # Update the local payment object's status if it has changed
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                return JsonResponse({
                    'status': 'requires_action',
                    'message': 'Payment requires further action or is pending. Please follow prompts provided by Stripe.'
                })

            else: # Covers 'failed', 'canceled', and other unexpected statuses
                # Payment failed or an unexpected status occurred
                if payment_obj:
                    # Update the local payment object's status if it has changed
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed or an unexpected status occurred. Please try again.'
                })

        except stripe.error.StripeError as e:
            # Handle Stripe API errors during intent retrieval
            print(f"Stripe Error in POST: {e}") # Log the error
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            # Handle any other unexpected errors
            print(f"General Error in POST: {e}") # Log the error
            return JsonResponse({'error': 'An internal server error occurred during payment processing.'}, status=500)
