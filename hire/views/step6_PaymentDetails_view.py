# hire/views/step6_PaymentDetails_view.py (Updated GET method)
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from hire.models import TempHireBooking
from payments.models import Payment
from django.conf import settings
import stripe

# Set your Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

class Step6PaymentDetailsView(View):
    def get(self, request):
        # Get the current temporary booking
        temp_booking_id = request.session.get('temp_booking_id')
        if not temp_booking_id:
            return redirect('hire:step1_select_datetime')  # Redirect to step 1 if no booking in session

        temp_booking = get_object_or_404(TempHireBooking, id=temp_booking_id)

        # Get the selected payment option from the TempHireBooking
        payment_option = temp_booking.payment_option

        amount_to_pay = None
        # Use the currency from the TempHireBooking if available, otherwise default
        currency = temp_booking.currency if hasattr(temp_booking, 'currency') and temp_booking.currency else 'dkk'

        if payment_option == 'online_full':
            amount_to_pay = temp_booking.grand_total
        elif payment_option == 'online_deposit':
            amount_to_pay = temp_booking.deposit_amount
        else:
            # If no valid payment option is set, redirect back to Step 5
            return redirect('hire:step5_summary_payment_options')

        if amount_to_pay is None:
            # If amount somehow wasn't determined, redirect back to Step 5
            return redirect('hire:step5_summary_payment_options')

        # Check if a Payment object already exists for this TempHireBooking
        # This prevents creating multiple PaymentIntents if the user refreshes the page
        payment_obj = Payment.objects.filter(temp_hire_booking=temp_booking).first()

        if payment_obj and payment_obj.stripe_payment_intent_id:
            # If Payment object exists and has an intent ID, retrieve existing intent
            try:
                intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)
                # Ensure the amount and currency match, update if necessary (e.g., if booking details changed)
                if intent.amount != int(amount_to_pay * 100) or intent.currency != currency:
                    intent = stripe.PaymentIntent.modify(
                        payment_obj.stripe_payment_intent_id,
                        amount=int(amount_to_pay * 100),
                        currency=currency
                    )
                    payment_obj.amount = amount_to_pay
                    payment_obj.currency = currency
                    payment_obj.save()
            except stripe.error.StripeError as e:
                # If retrieving fails, log and proceed to create a new one
                print(f"Stripe error retrieving existing PaymentIntent: {e}")
                payment_obj = None # Force creation of new PaymentIntent
        
        if not payment_obj: # If no existing valid payment object or retrieval failed
            try:
                # Create a new Payment Intent
                intent = stripe.PaymentIntent.create(
                    amount=int(amount_to_pay * 100),
                    currency=currency,
                    metadata={
                        'temp_booking_id': str(temp_booking.id),
                        'user_id': str(request.user.id) if request.user.is_authenticated else 'guest'
                    },
                    description=f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.make} {temp_booking.motorcycle.model}"
                )

                # Create a Payment object in your database and link it to the TempHireBooking
                payment = Payment.objects.create(
                    temp_hire_booking=temp_booking,
                    user=request.user if request.user.is_authenticated else None,
                    stripe_payment_intent_id=intent.id,
                    amount=amount_to_pay,
                    currency=currency,
                    status=intent.status, # Set initial status from Stripe
                    description=f"Motorcycle hire booking for {temp_booking.motorcycle.year} {temp_booking.motorcycle.make} {temp_booking.motorcycle.model}"
                )
                payment_obj = payment # Use the newly created object
            except stripe.error.StripeError as e:
                # Handle Stripe errors (log them, display a message to the user, etc.)
                print(f"Stripe error creating PaymentIntent: {e}")
                # Redirect back with an error message (you'll need to handle this in the template)
                # For a real app, you'd want a more user-friendly error page/message
                return redirect('hire:step5_summary_payment_options')


        context = {
            'client_secret': intent.client_secret,
            'amount': amount_to_pay,
            'currency': currency.upper(),
            'temp_booking': temp_booking,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY, # Pass the publishable key
        }
        return render(request, 'hire/step6_payment_details.html', context)

    def post(self, request):
        # This POST method will be used for confirming the payment status after client-side processing
        # We'll implement this in a later step, possibly using webhooks or a direct confirmation endpoint.
        pass

