# hire/views/step7_BookingConfirmation_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from hire.models import HireBooking # We will display the final HireBooking
from payments.models import Payment # Import the Payment model

class BookingConfirmationView(View):
    def get(self, request):
        """
        Displays the booking confirmation details after successful payment.
        It can retrieve the HireBooking either from the session's booking_reference
        or from a payment_intent_id passed in the URL query parameters.
        """
        print("DEBUG: Entering BookingConfirmationView GET method.")

        hire_booking = None
        
        # 1. Try to retrieve the final booking reference from the session (preferred)
        booking_reference = request.session.get('final_booking_reference')
        if booking_reference:
            try:
                hire_booking = get_object_or_404(HireBooking, booking_reference=booking_reference)
                print(f"DEBUG: Retrieved HireBooking from session: {hire_booking.booking_reference}")
            except HireBooking.DoesNotExist:
                print(f"DEBUG: HireBooking with reference {booking_reference} not found in DB, despite being in session.")
                # Fall through to try payment_intent_id
        else:
            print("DEBUG: No final_booking_reference in session.")

        # 2. If not found in session, try to retrieve using payment_intent_id from URL
        if not hire_booking:
            payment_intent_id = request.GET.get('payment_intent_id')
            if payment_intent_id:
                print(f"DEBUG: Attempting to retrieve HireBooking using payment_intent_id: {payment_intent_id}")
                try:
                    # Find the Payment object first
                    payment_obj = get_object_or_404(Payment, stripe_payment_intent_id=payment_intent_id)
                    # Then get the associated HireBooking
                    hire_booking = get_object_or_404(HireBooking, payment=payment_obj)
                    print(f"DEBUG: Retrieved HireBooking from Payment object: {hire_booking.booking_reference}")
                    
                    # If found this way, store the booking_reference in session for future use
                    request.session['final_booking_reference'] = hire_booking.booking_reference
                    print(f"DEBUG: Stored final_booking_reference: {hire_booking.booking_reference} in session for future use.")

                except Payment.DoesNotExist:
                    print(f"ERROR: Payment object with intent ID {payment_intent_id} not found.")
                except HireBooking.DoesNotExist:
                    print(f"ERROR: HireBooking not found for Payment object with intent ID {payment_intent_id}.")
            else:
                print("DEBUG: No payment_intent_id in URL query parameters.")

        # If after both attempts, no booking is found, redirect to start
        if not hire_booking:
            print("DEBUG: No HireBooking found by session or payment_intent_id. Redirecting to step 2.")
            return redirect('hire:step2_choose_bike')

        # Clear the session variable as the booking is now confirmed and persistent
        # It's good practice to clear it after successful retrieval to prevent
        # showing stale data or allowing re-access to this page without a new booking.
        if 'final_booking_reference' in request.session:
            del request.session['final_booking_reference']
            print("DEBUG: Cleared 'final_booking_reference' from session.")
        
        # Also clear the temp_booking_id if it somehow still exists here
        if 'temp_booking_id' in request.session:
            del request.session['temp_booking_id']
            print("DEBUG: Cleared 'temp_booking_id' from session.")


        context = {
            'hire_booking': hire_booking,
            'booking_status': hire_booking.status,
            'payment_status': hire_booking.payment_status,
            'total_price': hire_booking.total_price,
            'amount_paid': hire_booking.amount_paid,
            'currency': hire_booking.currency,
            'motorcycle_details': f"{hire_booking.motorcycle.year} {hire_booking.motorcycle.brand} {hire_booking.motorcycle.model}",
            'pickup_datetime': f"{hire_booking.pickup_date} at {hire_booking.pickup_time}",
            'return_datetime': f"{hire_booking.return_date} at {hire_booking.return_time}",
            'driver_name': hire_booking.driver_profile.name, # Use .name instead of .full_name if full_name is not a property
            'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
            'addons': hire_booking.booking_addons.all(), # Get all BookingAddOn instances linked to this HireBooking
        }
        print("DEBUG: Rendering step7_booking_confirmation.html with context.")
        return render(request, 'hire/step7_booking_confirmation.html', context)

