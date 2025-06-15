# payments/utils/ajax_get_sales_booking_details.py

from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.utils import timezone

from inventory.models import SalesBooking # Import SalesBooking model
from payments.models import RefundRequest
from payments.utils.sales_refund_calc import calculate_sales_refund_amount # Import the sales refund calculator


@require_GET
@login_required
def get_sales_booking_details_json(request, pk):
    """
    AJAX endpoint to retrieve details for a SalesBooking, including refund calculation.
    Requires staff authentication.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        sales_booking = get_object_or_404(SalesBooking, pk=pk)

        customer_name = 'N/A'
        customer_email = 'N/A'
        if sales_booking.sales_profile:
            customer_name = sales_booking.sales_profile.name if sales_booking.sales_profile.name else 'N/A'
            customer_email = sales_booking.sales_profile.email if sales_booking.sales_profile.email else 'N/A'
            # If linked to a user, prefer user's full name/email
            if sales_booking.sales_profile.user:
                if sales_booking.sales_profile.user.get_full_name():
                    customer_name = sales_booking.sales_profile.user.get_full_name()
                customer_email = sales_booking.sales_profile.user.email

        motorcycle_details = {
            'year': sales_booking.motorcycle.year if sales_booking.motorcycle else 'N/A',
            'brand': sales_booking.motorcycle.brand if sales_booking.motorcycle else 'N/A',
            'model': sales_booking.motorcycle.model if sales_booking.motorcycle else 'N/A',
            'vin': sales_booking.motorcycle.vin if sales_booking.motorcycle else 'N/A',
        }

        payment_date = sales_booking.payment.created_at.strftime('%Y-%m-%d %H:%M') if sales_booking.payment and sales_booking.payment.created_at else 'N/A'
        payment_amount = float(sales_booking.payment.amount) if sales_booking.payment and sales_booking.payment.amount is not None else 'N/A'

        refund_status_for_booking = 'No Refund Request Yet'
        latest_refund_request = RefundRequest.objects.filter(sales_booking=sales_booking).order_by('-requested_at').first()
        if latest_refund_request:
            refund_status_for_booking = latest_refund_request.get_status_display()

        # Get refund policy snapshot from the payment object
        refund_policy_snapshot_for_calc = {}
        if sales_booking.payment and sales_booking.payment.refund_policy_snapshot:
            refund_policy_snapshot_for_calc = sales_booking.payment.refund_policy_snapshot

        # The sales refund calculation uses the booking's created_at as the reference point
        # for grace period calculation, not an appointment date.
        # The cancellation_datetime for the refund calc should be the current time or
        # the time the refund request was made (refund_request.requested_at if available and verified).
        # For this AJAX view, we can use timezone.now() as a default for simulation purposes.
        cancellation_datetime_for_calc = timezone.now() # Using now() for real-time calculation in AJAX

        refund_calculation_results = calculate_sales_refund_amount(
            booking=sales_booking,
            cancellation_datetime=cancellation_datetime_for_calc,
            refund_policy_snapshot=refund_policy_snapshot_for_calc
        )

        booking_details = {
            'id': sales_booking.id,
            'sales_booking_reference': sales_booking.sales_booking_reference,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'motorcycle_details': motorcycle_details,
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'booking_status': sales_booking.get_booking_status_display(),
            'payment_status': sales_booking.get_payment_status_display(),
            'customer_notes': sales_booking.customer_notes if sales_booking.customer_notes else '',
            'request_viewing': sales_booking.request_viewing,
            'appointment_date': sales_booking.appointment_date.strftime('%Y-%m-%d') if sales_booking.appointment_date else 'N/A',
            'appointment_time': sales_booking.appointment_time.strftime('%H:%M') if sales_booking.appointment_time else 'N/A',
            'entitled_refund_amount': float(refund_calculation_results['entitled_amount']),
            'refund_calculation_details': refund_calculation_results['details'],
            'refund_policy_applied': refund_calculation_results['policy_applied'],
            'time_since_booking_creation_hours': refund_calculation_results['time_since_booking_creation_hours'],
            'refund_request_status_for_booking': refund_status_for_booking,
        }
        return JsonResponse(booking_details)
    except Http404:
        return JsonResponse({'error': 'Sales Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
