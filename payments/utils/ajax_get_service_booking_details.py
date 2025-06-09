# payments/utils/ajax_get_service_booking_details.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.utils import timezone

# Import ServiceBooking and RefundRequest models
from service.models import ServiceBooking
from payments.models import RefundRequest
from payments.utils.service_refund_calc import calculate_service_refund_amount

@require_GET
@login_required # Assuming staff login is required for this internal API
def get_service_booking_details_json(request, pk):
    """
    API endpoint to return details of a specific ServiceBooking as JSON.
    Requires staff login. This endpoint also includes the latest
    refund request status associated with the booking.
    """
    try:
        service_booking = get_object_or_404(ServiceBooking, pk=pk)

        customer_name = 'N/A'
        # Logic to get customer name from service_profile
        if service_booking.service_profile:
            if service_booking.service_profile.user:
                user_full_name = service_booking.service_profile.user.get_full_name()
                if user_full_name:
                    customer_name = user_full_name
                elif service_booking.service_profile.name:
                    customer_name = service_booking.service_profile.name
            elif service_booking.service_profile.name:
                customer_name = service_booking.service_profile.name

        payment_date = 'N/A'
        payment_amount = 'N/A'
        
        # *** FIX: Ensure refund_policy_snapshot is always a dictionary. ***
        # If payment exists, use its snapshot, otherwise default to an empty dictionary.
        # This prevents an error if payment.refund_policy_snapshot is None.
        refund_policy_snapshot = (service_booking.payment.refund_policy_snapshot or {}) if service_booking.payment else {}


        # Fetch payment details from the linked Payment object
        if service_booking.payment:
            payment_date = service_booking.payment.created_at.strftime('%Y-%m-%d %H:%M') if service_booking.payment.created_at else 'N/A'
            payment_amount = float(service_booking.payment.amount) if service_booking.payment.amount else 'N/A'
        
        # Get the latest refund request for this service booking
        latest_refund_request = RefundRequest.objects.filter(service_booking=service_booking).order_by('-requested_at').first()
        refund_status_for_booking = latest_refund_request.get_status_display() if latest_refund_request else 'No Refund Request Yet'

        # Calculate potential refund amount using the service-specific calculator
        refund_calculation_results = calculate_service_refund_amount(
            booking=service_booking,
            refund_policy_snapshot=refund_policy_snapshot,
            cancellation_datetime=timezone.now()
        )

        # Prepare details about the customer's motorcycle for service
        motorcycle_details = {
            'year': service_booking.customer_motorcycle.year if service_booking.customer_motorcycle else 'N/A',
            'brand': service_booking.customer_motorcycle.brand if service_booking.customer_motorcycle else 'N/A',
            'model': service_booking.customer_motorcycle.model if service_booking.customer_motorcycle else 'N/A',
        }
        
        # Prepare service type details
        service_type_details = {
            'name': service_booking.service_type.name if service_booking.service_type else 'N/A',
            'description': service_booking.service_type.description if service_booking.service_type else 'N/A',
        }


        booking_details = {
            'id': service_booking.id,
            'service_booking_reference': service_booking.service_booking_reference,
            'customer_name': customer_name,
            'service_date': service_booking.service_date.strftime('%Y-%m-%d') if service_booking.service_date else 'N/A',
            'dropoff_date': service_booking.dropoff_date.strftime('%Y-%m-%d') if service_booking.dropoff_date else 'N/A',
            'dropoff_time': service_booking.dropoff_time.strftime('%H:%M') if service_booking.dropoff_time else 'N/A',
            'estimated_pickup_date': service_booking.estimated_pickup_date.strftime('%Y-%m-%d') if service_booking.estimated_pickup_date else 'N/A',
            'motorcycle_details': motorcycle_details, # Nested motorcycle details
            'service_type_details': service_type_details, # Nested service type details
            'payment_option': service_booking.get_payment_option_display() if service_booking.payment_option else 'N/A',
            'payment_date': payment_date,
            'payment_amount': payment_amount,
            'booking_status': service_booking.get_booking_status_display(),
            'payment_status': service_booking.get_payment_status_display(),
            'customer_notes': service_booking.customer_notes if service_booking.customer_notes else '',
            'entitled_refund_amount': float(refund_calculation_results['entitled_amount']),
            'refund_calculation_details': refund_calculation_results['details'],
            'refund_policy_applied': refund_calculation_results['policy_applied'],
            'refund_days_before_dropoff': refund_calculation_results['days_before_dropoff'], # Updated key
            'refund_request_status_for_booking': refund_status_for_booking,
        }
        return JsonResponse(booking_details)
    except ServiceBooking.DoesNotExist:
        return JsonResponse({'error': 'Service Booking not found'}, status=404)
    except Exception as e:
        # It's helpful to log the actual exception for debugging
        print(f"Error in get_service_booking_details_json: {e}")
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
