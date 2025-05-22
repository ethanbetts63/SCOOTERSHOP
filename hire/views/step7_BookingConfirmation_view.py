# hire/views/step7_BookingConfirmation_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from hire.models import HireBooking # We will display the final HireBooking

class BookingConfirmationView(View):
    def get(self, request):
        """
        Displays the booking confirmation details after successful payment.
        """
        print("DEBUG: Entering BookingConfirmationView GET method.")

        # Retrieve the final booking reference from the session
        booking_reference = request.session.get('final_booking_reference')

        if not booking_reference:
            print("DEBUG: No final_booking_reference in session. Redirecting to step 1.")
            # If no booking reference, redirect to the start of the booking process
            return redirect('hire:step1_select_datetime')

        try:
            # Fetch the confirmed HireBooking object
            hire_booking = get_object_or_404(HireBooking, booking_reference=booking_reference)
            print(f"DEBUG: Retrieved HireBooking: {hire_booking.booking_reference}")

            # Clear the session variable as the booking is now confirmed and persistent
            # It's good practice to clear it after successful retrieval to prevent
            # showing stale data or allowing re-access to this page without a new booking.
            if 'final_booking_reference' in request.session:
                del request.session['final_booking_reference']
                print("DEBUG: Cleared 'final_booking_reference' from session.")

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
                'driver_name': hire_booking.driver_profile.full_name,
                'package_name': hire_booking.package.name if hire_booking.package else 'N/A',
                'addons': hire_booking.booking_addons.all(), # Get all BookingAddOn instances linked to this HireBooking
            }
            print("DEBUG: Rendering step7_booking_confirmation.html with context.")
            return render(request, 'hire/step7_booking_confirmation.html', context)

        except HireBooking.DoesNotExist:
            print(f"ERROR: HireBooking with reference {booking_reference} not found.")
            # If the booking is not found, something went wrong, redirect to a generic error or start page
            return redirect('hire:step1_select_datetime')
        except Exception as e:
            print(f"An unexpected error occurred in BookingConfirmationView: {e}")
            # Log the full traceback for debugging in production
            import traceback
            traceback.print_exc()
            return redirect('hire:step1_select_datetime') # Redirect to start on error

