# hire/views/step6_PaymentDetails_view.py (Updated GET method with debug prints and attribute fix)
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from hire.models import TempHireBooking
from payments.models import Payment
from django.conf import settings
import stripe

# Set your Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentDetailsView(View):
    def get(self, request):
        # Get the current temporary booking
        temp_booking_id = request.session.get('temp_booking_id')
        print(f"DEBUG: In Step6PaymentDetailsView GET. temp_booking_id from session: {temp_booking_id}")

        if not temp_booking_id:
            print("DEBUG: No temp_booking_id in session. Redirecting to step 1.")
            return redirect('hire:step1_select_datetime')  # Redirect to step 1 if no booking in session

        temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)
        print(f"DEBUG: Retrieved TempHireBooking: {temp_booking.id}")

        # Get the selected payment option from the TempHireBooking
        payment_option = temp_booking.payment_option
        print(f"DEBUG: TempHireBooking payment_option: {payment_option}")

        amount_to_pay = None
        # Use the currency from the TempHireBooking if available, otherwise default
        currency = temp_booking.currency if hasattr(temp_booking, 'currency') and temp_booking.currency else 'dkk'
        print(f"DEBUG: TempHireBooking currency: {currency}")


        if payment_option == 'online_full':
            amount_to_pay = temp_booking.grand_total
            print(f"DEBUG: Payment option 'online_full'. Amount to pay: {amount_to_pay}")
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.deposit_amount
            print(f"DEBUG: Payment option 'online_deposit'. Amount to pay: {amount_to_pay}")
        else:
            # If no valid payment option is set, redirect back to Step 5
            print(f"DEBUG: Invalid payment option '{payment_option}'. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        if amount_to_pay is None:
            # If amount somehow wasn't determined, redirect back to Step 5
            print("DEBUG: amount_to_pay is None. Redirecting to step 5.")
            return redirect('hire:step5_summary_payment_options')

        # Check if a Payment object already exists for this TempHireBooking
        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()

        # Construct a description for the payment intent
        # FIX: Changed 'make' to 'brand' as per Motorcycle model
        payment_description = f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.brand} {temp_booking.motorcycle.model}"


        if payment_obj and payment_obj.stripe_payment_intent_id:
            print(f"DEBUG: Existing Payment object found: {payment_obj.id}, Stripe Intent ID: {payment_obj.stripe_payment_intent_id}")
            try:
                intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)
                print(f"DEBUG: Retrieved Stripe PaymentIntent: {intent.id}, Status: {intent.status}")
                
                # Ensure the amount and currency match, update if necessary
                if intent.amount != int(amount_to_pay * 100) or intent.currency.lower() != currency.lower():
                    print(f"DEBUG: Mismatch in amount/currency. Modifying PaymentIntent.")
                    intent = stripe.PaymentIntent.modify(
                        payment_obj.stripe_payment_intent_id,
                        amount=int(amount_to_pay * 100),
                        currency=currency,
                        description=payment_description # Update description if needed
                    )
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.description = payment_description # Update description in DB
                    payment_obj.save()
                    print(f"DEBUG: Modified PaymentIntent: {intent.id}, New Amount: {intent.amount}, New Currency: {intent.currency}")
            except stripe.error.StripeError as e:
                print(f"Stripe error retrieving existing PaymentIntent: {e}. Forcing creation of new one.")
                payment_obj = None # Force creation of new PaymentIntent
        
        if not payment_obj: # If no existing valid payment object or retrieval failed
            print("DEBUG: No existing Payment object or retrieval failed. Creating new PaymentIntent.")
            try:
                # Create a new Payment Intent
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100), # Stripe expects amount in cents
                    currency=currency,
                    metadata={
                        'temp_booking_id': str(temp_booking.id),
                        'user_id': str(request.user.id) if request.user.is_authenticated else 'guest'
                    },
                    description=payment_description # Use the corrected description
                )
                print(f"DEBUG: Created new Stripe PaymentIntent: {intent.id}, Client Secret: {intent.client_secret}, Status: {intent.status}")

                # Create a Payment object in your database and link it to the TempHireBooking
                payment = Payment.objects.create(
                    temp_hire_booking=temp_booking,
                    user=request.user if request.user.is_authenticated else None,
                    stripe_payment_intent_id=intent.id,
                    amount=amount_to_pay,
                    currency=currency,
                    status=intent.status, # Set initial status from Stripe
                    description=payment_description # Use the corrected description
                )
                payment_obj = payment # Use the newly created object
                print(f"DEBUG: Created new Payment DB object: {payment_obj.id}")
            except stripe.error.StripeError as e:
                print(f"Stripe error creating PaymentIntent: {e}")
                return redirect('hire:step5_summary_payment_options')


        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY, # Pass the publishable key
        }
        print("DEBUG: Rendering step6_payment_details.html with context.")
        return render(request, 'hire/step6_payment_details.html', context)

    def post(self, request):
        # This POST method will be used for confirming the payment status after client-side processing
        # We'll implement this in a later step, possibly using webhooks or a direct confirmation endpoint.
        pass
