from django.http import JsonResponse, Http404 # Import Http404
from django.shortcuts import get_object_or_404
from hire.models import HireBooking
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.utils import timezone
from payments.utils.hire_refund_calc import calculate_hire_refund_amount
from payments.models import RefundRequest
from datetime import datetime # Import datetime for combine

@require_GET
@login_required
def get_hire_booking_details_json(request, pk):
    """
    API endpoint to return details of a specific HireBooking as JSON.
    Requires staff login. This endpoint now also includes the latest
    refund request status associated with the booking.
    """
    # Manual check for staff status
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        hire_booking = get_object_or_404(HireBooking, pk=pk)

        customer_name = 'N/A'

        if hire_booking.driver_profile:
            if hire_booking.driver_profile.user:
                user_full_name = hire_booking.driver_profile.user.get_full_name()
                if user_full_name:
                    customer_name = user_full_name
                elif hire_booking.driver_profile.name:
                    customer_name = hire_booking.driver_profile.name
            elif hire_booking.driver_profile.name:
                customer_name = hire_booking.driver_profile.name

        payment_date = 'N/A'
        payment_amount = 'N/A'
        refund_policy_snapshot = {}
        if hire_booking.payment:
            payment_date = hire_booking.payment.created_at.strftime('%Y-%m-%d %H:%M') if hire_booking.payment.created_at else 'N/A'
            payment_amount = float(hire_booking.payment.amount) if hire_booking.payment.amount is not None else 'N/A'
            refund_policy_snapshot = hire_booking.payment.refund_policy_snapshot if hire_booking.payment.refund_policy_snapshot else {}
        else:
            pass # Keep payment_date and payment_amount as 'N/A'

        latest_refund_request = RefundRequest.objects.filter(hire_booking=hire_booking).order_by('-requested_at').first()
        refund_status_for_booking = latest_refund_request.get_status_display() if latest_refund_request else 'No Refund Request Yet'

        # Construct cancellation_datetime from pickup_date and pickup_time
        cancellation_datetime = datetime.combine(hire_booking.pickup_date, hire_booking.pickup_time)
        if timezone.is_aware(timezone.now()): # Check if current timezone is aware
            cancellation_datetime = timezone.make_aware(cancellation_datetime) # Make it aware if timezone is active


        refund_calculation_results = calculate_hire_refund_amount(
            booking=hire_booking,
            refund_policy_snapshot=refund_policy_snapshot,
            cancellation_datetime=cancellation_datetime # Use the constructed cancellation_datetime
        )

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
            'entitled_refund_amount': float(refund_calculation_results['entitled_amount']),
            'refund_calculation_details': refund_calculation_results['details'],
            'refund_policy_applied': refund_calculation_results['policy_applied'],
            'refund_days_before_pickup': refund_calculation_results['days_before_pickup'],
            'refund_request_status_for_booking': refund_status_for_booking,
        }
        return JsonResponse(booking_details)
    except Http404: # Catch Http404 specifically for 404 response
        return JsonResponse({'error': 'Hire Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
