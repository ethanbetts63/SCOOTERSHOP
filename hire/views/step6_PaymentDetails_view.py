# hire/views/step6_PaymentDetails_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction

from hire.models import TempHireBooking, HireBooking, BookingAddOn, TempBookingAddOn
from payments.models import Payment
from django.conf import settings
import stripe
import json

# Set your Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentDetailsView(View):
    def get(self, request):
        """
        Handles GET requests to display the payment form and create/retrieve Stripe PaymentIntent.
        """
        temp_booking_id = request.session.get('temp_booking_id')
        print(f"DEBUG: In Step6PaymentDetailsView GET. temp_booking_id from session: {temp_booking_id}")

        if not temp_booking_id:
            print("DEBUG: No temp_booking_id in session. Redirecting to step 1.")
            return redirect('hire:step1_select_datetime')

        temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)
        print(f"DEBUG: Retrieved TempHireBooking: {temp_booking.id}")

        payment_option = temp_booking.payment_option
        print(f"DEBUG: TempHireBooking payment_option: {payment_option}")

        amount_to_pay = None
        currency = temp_booking.currency if hasattr(temp_booking, 'currency') and temp_booking.currency else 'AUD'
        print(f"DEBUG: TempHireBooking currency: {currency}")

        if payment_option == 'online_full':
            amount_to_pay = temp_booking.grand_total
            print(f"DEBUG: Payment option 'online_full'. Amount to pay: {amount_to_pay}")
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.deposit_amount
            print(f"DEBUG: Payment option 'online_deposit'. Amount to pay: {amount_to_pay}")
        else:
            print(f"DEBUG: Invalid payment option '{payment_option}'. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        if amount_to_pay is None:
            print("DEBUG: amount_to_pay is None. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        payment_description = f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"

        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()
        intent = None # Initialize intent to None

        # --- Logic to handle existing payment objects and Stripe PaymentIntents ---
        if payment_obj and payment_obj.stripe_payment_intent_id:
            try:
                # Retrieve the existing Stripe PaymentIntent
                intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)
                print(f"DEBUG: Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")

                # If the PaymentIntent has already succeeded, redirect to confirmation
                if intent.status == 'succeeded':
                    print(f"DEBUG: Existing Stripe PaymentIntent {intent.id} is already succeeded. Redirecting to confirmation.")
                    
                    # Update the Payment object's status in case it's out of sync
                    if payment_obj.status != 'succeeded':
                        payment_obj.status = 'succeeded'
                        payment_obj.save()
                        print(f"DEBUG: Updated Payment DB object {payment_obj.id} status to 'succeeded'.")

                    # Ensure HireBooking is created if not already
                    # This check is a heuristic; ideally, TempHireBooking would have a OneToOneField to HireBooking
                    hire_booking = HireBooking.objects.filter(
                        motorcycle=temp_booking.motorcycle,
                        pickup_date=temp_booking.pickup_date,
                        return_date=temp_booking.return_date,
                        total_price=temp_booking.grand_total # This might not be unique enough in all cases
                    ).first()

                    if not hire_booking:
                         print("DEBUG: HireBooking not found for this TempHireBooking. Attempting to create it.")
                         with transaction.atomic():
                             hire_booking = self._create_hire_booking_from_temp(temp_booking, payment_obj)
                             print(f"DEBUG: Created HireBooking: {hire_booking.booking_reference}")
                    
                    if hire_booking:
                        request.session['final_booking_reference'] = hire_booking.booking_reference
                        # Clear the temp_booking_id from session as it's now finalized
                        if 'temp_booking_id' in request.session:
                            del request.session['temp_booking_id']
                            print(f"DEBUG: Cleared temp_booking_id {temp_booking_id} from session.")
                        return redirect('hire:step7_confirmation')
                    else:
                        print("ERROR: Could not create HireBooking despite succeeded payment. Redirecting to step 1.")
                        return redirect('hire:step1_select_datetime')

                # If the PaymentIntent is not succeeded, check if it needs modification or a new one
                amount_changed = intent.amount != int(amount_to_pay * 100)
                currency_changed = intent.currency.lower() != currency.lower()
                
                # Check if the intent is in a modifiable state
                is_modifiable = intent.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']

                if (amount_changed or currency_changed) and is_modifiable:
                    print(f"DEBUG: Mismatch in amount/currency for modifiable intent. Modifying PaymentIntent {intent.id}.")
                    intent = stripe.PaymentIntent.modify(
                        payment_obj.stripe_payment_intent_id,
                        amount=int(amount_to_pay * 100),
                        currency=currency,
                        description=payment_description
                    )
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status # Update status after modification
                    payment_obj.description = payment_description
                    payment_obj.save()
                    print(f"DEBUG: Modified PaymentIntent: {intent.id}, New Amount: {intent.amount}, New Currency: {intent.currency}")
                elif not is_modifiable and intent.status not in ['succeeded', 'canceled', 'failed']:
                     # If it's not modifiable and not succeeded/canceled/failed, something is odd.
                     # Treat as if no valid intent exists and create a new one.
                     print(f"DEBUG: Existing PaymentIntent {intent.id} is not modifiable ({intent.status}) and not succeeded/canceled/failed. Forcing creation of new one.")
                     payment_obj = None # This will lead to new intent creation below
                     intent = None # Reset intent as it's no longer valid for this flow
                elif intent.status in ['canceled', 'failed']:
                    # If the existing intent is canceled or failed, we need a new one
                    print(f"DEBUG: Existing PaymentIntent {intent.id} is {intent.status}. Forcing creation of new one.")
                    payment_obj = None # This will lead to new intent creation below
                    intent = None # Reset intent as it's no longer valid for this flow
                else:
                    # If intent exists, is modifiable, and amounts/currencies match, just use it.
                    # Or if it's processing, we still use it.
                    print(f"DEBUG: Re-using existing PaymentIntent {intent.id} (Status: {intent.status}).")
                    # Ensure local DB status is up-to-date
                    if payment_obj.status != intent.status:
                        payment_obj.status = intent.status
                        payment_obj.save()

            except stripe.error.StripeError as e:
                print(f"Stripe error retrieving or modifying existing PaymentIntent ({payment_obj.stripe_payment_intent_id}): {e}. Forcing creation of new one.")
                payment_obj = None # Force creation of new PaymentIntent/Payment object
                intent = None # Reset intent as it's no longer valid

        # --- If no valid intent or payment_obj, create a new one ---
        if not payment_obj or not intent:
            print("DEBUG: Creating new Stripe PaymentIntent and Payment DB object.")
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100), # Stripe expects amount in cents
                    currency=currency,
                    metadata={
                        'temp_booking_id': str(temp_booking.id),
                        'user_id': str(request.user.id) if request.user.is_authenticated else 'guest'
                    },
                    description=payment_description
                )
                print(f"DEBUG: Created new Stripe PaymentIntent: {intent.id}, Client Secret: {intent.client_secret}, Status: {intent.status}")

                # Create or update the Payment object
                if payment_obj: # If payment_obj existed but was invalidated (e.g., old intent failed/canceled)
                    payment_obj.stripe_payment_intent_id = intent.id
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.status = intent.status
                    payment_obj.description = payment_description
                    payment_obj.save()
                    print(f"DEBUG: Updated existing Payment DB object: {payment_obj.id} with new Stripe Intent.")
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
                    print(f"DEBUG: Created new Payment DB object: {payment_obj.id}")
            except stripe.error.StripeError as e:
                print(f"Stripe error creating PaymentIntent: {e}")
                return redirect('hire:step5_summary_payment_options')

        # Ensure intent is not None before passing to context
        if not intent:
            print("ERROR: PaymentIntent could not be created or retrieved. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        print("DEBUG: Rendering step6_payment_details.html with context.")
        return render(request, 'hire/step6_payment_details.html', context)

    def post(self, request):
        """
        Handles POST requests to confirm payment status after client-side processing
        and finalize the booking.
        """
        print("DEBUG: Entering Step6PaymentDetailsView POST method.")
        
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
            print(f"DEBUG: Received payment_intent_id: {payment_intent_id}")
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON in request body.")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not payment_intent_id:
            print("ERROR: No payment_intent_id provided in POST request.")
            return JsonResponse({'error': 'Payment Intent ID is required'}, status=400)

        try:
            # Retrieve the Payment Intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            print(f"DEBUG: Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")

            # Find the corresponding Payment object in your database
            payment_obj = get_object_or_404(Payment, stripe_payment_intent_id=intent.id)
            temp_booking = payment_obj.temp_hire_booking
            print(f"DEBUG: Found Payment DB object: {payment_obj.id} for TempHireBooking: {temp_booking.id}")

            # Update the Payment object status
            payment_obj.status = intent.status
            payment_obj.save()
            print(f"DEBUG: Updated Payment DB object status to: {payment_obj.status}")

            # Handle different Stripe Payment Intent statuses
            if intent.status == 'succeeded':
                print("DEBUG: Payment Intent succeeded. Finalizing booking.")
                with transaction.atomic():
                    hire_booking = self._create_hire_booking_from_temp(temp_booking, payment_obj)
                    print(f"DEBUG: Created HireBooking: {hire_booking.booking_reference}")

                    # --- IMPORTANT: Delete the TempHireBooking after successful conversion ---
                    temp_booking_id_to_delete = temp_booking.id # Store ID before deleting object
                    temp_booking.delete()
                    print(f"DEBUG: TempHireBooking {temp_booking_id_to_delete} and associated TempBookingAddOns deleted.")

                # Clear the temp_booking_id from session as it's now finalized
                if 'temp_booking_id' in request.session:
                    del request.session['temp_booking_id']
                    print(f"DEBUG: Cleared temp_booking_id from session.")

                # Redirect to the confirmation page with the new booking reference
                request.session['final_booking_reference'] = hire_booking.booking_reference
                print(f"DEBUG: Redirecting to success with booking reference: {hire_booking.booking_reference}")
                return JsonResponse({'status': 'success', 'redirect_url': '/hire/confirmation/'})

            elif intent.status in ['requires_action', 'requires_confirmation', 'requires_payment_method']:
                print(f"DEBUG: Payment Intent requires further action or is pending: {intent.status}")
                return JsonResponse({'status': 'requires_action', 'redirect_url': '/hire/payment_failed/'})

            else:
                print(f"DEBUG: Payment Intent status is unexpected: {intent.status}")
                return JsonResponse({'status': 'failed', 'redirect_url': '/hire/payment_failed/'})

        except stripe.error.StripeError as e:
            print(f"Stripe API Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
        except Payment.DoesNotExist:
            print(f"ERROR: Payment object not found for Stripe Intent ID: {payment_intent_id}")
            return JsonResponse({'error': 'Payment record not found in DB'}, status=404)
        except Exception as e:
            print(f"An unexpected error occurred in POST: {e}")
            # Log the full traceback for debugging
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': 'An internal server error occurred'}, status=500)


    def _create_hire_booking_from_temp(self, temp_booking, payment_obj):
        """
        Helper method to create a permanent HireBooking from a TempHireBooking.
        This should be called only after successful payment.
        """
        print(f"DEBUG: _create_hire_booking_from_temp called for TempHireBooking: {temp_booking.id}")

        # Determine payment_status for the HireBooking based on the original payment option
        hire_payment_status = 'paid' if temp_booking.payment_option == 'online_full' else 'deposit_paid'

        # Create the HireBooking instance
        hire_booking = HireBooking.objects.create(
            motorcycle=temp_booking.motorcycle,
            driver_profile=temp_booking.driver_profile,
            package=temp_booking.package,
            booked_package_price=temp_booking.booked_package_price,
            pickup_date=temp_booking.pickup_date,
            pickup_time=temp_booking.pickup_time,
            return_date=temp_booking.return_date,
            return_time=temp_booking.return_time,
            is_international_booking=temp_booking.is_international_booking,
            booked_daily_rate=temp_booking.booked_daily_rate,
            total_price=temp_booking.grand_total,
            deposit_amount=temp_booking.deposit_amount if temp_booking.deposit_amount else 0,
            amount_paid=payment_obj.amount,
            payment_status=hire_payment_status,
            payment_method='online',
            currency=temp_booking.currency,
            status='confirmed',
        )
        print(f"DEBUG: New HireBooking created with ID: {hire_booking.id}, Reference: {hire_booking.booking_reference}")

        # Copy add-ons from TempBookingAddOn to BookingAddOn
        temp_booking_addons = TempBookingAddOn.objects.filter(temp_booking=temp_booking)
        for temp_addon in temp_booking_addons:
            BookingAddOn.objects.create(
                booking=hire_booking,
                addon=temp_addon.addon,
                quantity=temp_addon.quantity,
                booked_addon_price=temp_addon.booked_addon_price
            )
            print(f"DEBUG: Copied add-on '{temp_addon.addon.name}' (Qty: {temp_addon.quantity}) to HireBooking {hire_booking.booking_reference}")
        
        return hire_booking

