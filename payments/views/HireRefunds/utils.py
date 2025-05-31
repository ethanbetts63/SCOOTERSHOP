# payments/views/HireRefunds/utils.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from hire.models import HireBooking
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
import json
from datetime import datetime
from django.utils import timezone
from payments.hire_refund_calc import calculate_refund_amount # Import the correct calculator

@require_GET
@login_required
def get_hire_booking_details_json(request, pk):
    """
    API endpoint to return details of a specific HireBooking as JSON.
    Requires staff login.
    """
    print(f"DEBUG: Entering get_hire_booking_details_json for PK: {pk}")
    try:
        hire_booking = get_object_or_404(HireBooking, pk=pk)
        print(f"DEBUG: Successfully retrieved HireBooking with ID: {hire_booking.id}")

        # Debugging driver profile and user details
        print(f"DEBUG: hire_booking.driver_profile: {hire_booking.driver_profile}")
        customer_name = 'N/A' # Default to N/A

        if hire_booking.driver_profile:
            print(f"DEBUG: driver_profile.name: {hire_booking.driver_profile.name}")
            print(f"DEBUG: driver_profile.user: {hire_booking.driver_profile.user}")

            if hire_booking.driver_profile.user:
                user_full_name = hire_booking.driver_profile.user.get_full_name()
                print(f"DEBUG: driver_profile.user.get_full_name(): '{user_full_name}'")
                if user_full_name: # If get_full_name() returns a non-empty string
                    customer_name = user_full_name
                elif hire_booking.driver_profile.name: # Fallback to driver_profile.name if user full name is empty
                    customer_name = hire_booking.driver_profile.name
            elif hire_booking.driver_profile.name: # If no user linked, use driver_profile.name
                customer_name = hire_booking.driver_profile.name
        print(f"DEBUG: Final customer_name determined: '{customer_name}'")

        # Debugging payment details
        print(f"DEBUG: Checking hire_booking.payment: {hire_booking.payment}")
        payment_date = 'N/A'
        payment_amount = 'N/A'
        refund_policy_snapshot = {} # Initialize empty snapshot
        if hire_booking.payment:
            print(f"DEBUG: Payment object exists. Created at: {hire_booking.payment.created_at}, Amount: {hire_booking.payment.amount}")
            payment_date = hire_booking.payment.created_at.strftime('%Y-%m-%d %H:%M') if hire_booking.payment.created_at else 'N/A'
            payment_amount = float(hire_booking.payment.amount) if hire_booking.payment.amount else 'N/A'
            refund_policy_snapshot = hire_booking.payment.refund_policy_snapshot
            print(f"DEBUG: Retrieved refund_policy_snapshot: {refund_policy_snapshot}")
        else:
            print("DEBUG: hire_booking.payment is None. No refund policy snapshot available for calculation.")

        # Calculate entitled refund amount using the new utility
        # Pass the retrieved refund_policy_snapshot
        refund_calculation_results = calculate_refund_amount(
            booking=hire_booking,
            refund_policy_snapshot=refund_policy_snapshot, # Pass the snapshot here
            cancellation_datetime=timezone.now() # Or you could pass a specific cancellation date from request if available
        )
        print(f"DEBUG: Refund calculation results: {refund_calculation_results}")

        # Basic details of the chosen hire booking
        booking_details = {
            'id': hire_booking.id,
            'booking_reference': hire_booking.booking_reference,
            'customer_name': customer_name,
            'pickup_date': hire_booking.pickup_date.strftime('%Y-%m-%d') if hire_booking.pickup_date else 'N/A',
            'pickup_time': hire_booking.pickup_time.strftime('%H:%M') if hire_booking.pickup_time else 'N/A',
            'return_date': hire_booking.return_date.strftime('%Y-%m-%d') if hire_booking.return_date else 'N/A',
            'return_time': hire_booking.return_time.strftime('%H:%M') if hire_booking.return_time else 'N/A',
            'motorcycle_year': hire_booking.motorcycle.year if hire_booking.motorcycle else 'N/A',
            'motorcycle_brand': hire_booking.motorcycle.brand if hire_booking.motorcycle else 'N/A',
            'motorcycle_model': hire_booking.motorcycle.model if hire_booking.motorcycle else 'N/A',
            'payment_method': hire_booking.get_payment_method_display() if hire_booking.payment_method else 'N/A',
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'booking_status': hire_booking.get_status_display(),
            'payment_status': hire_booking.get_payment_status_display(),
            'entitled_refund_amount': float(refund_calculation_results['entitled_amount']), # Add calculated refund
            'refund_calculation_details': refund_calculation_results['details'], # Add calculation details
            'refund_policy_applied': refund_calculation_results['policy_applied'],
            'refund_days_before_pickup': refund_calculation_results['days_before_pickup'],
            # Add any other details you might need
        }
        print(f"DEBUG: Constructed booking_details: {booking_details}")
        return JsonResponse(booking_details)
    except HireBooking.DoesNotExist:
        print(f"DEBUG: HireBooking with PK {pk} not found.")
        return JsonResponse({'error': 'Hire Booking not found'}, status=404)
    except Exception as e:
        print(f"DEBUG: An unexpected error occurred while fetching booking details for PK {pk}: {str(e)}")
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
