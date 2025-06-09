# payments/utils/ajax_get_service_booking_details.py

from django.http import JsonResponse, Http404 
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test # Changed staff_member_required to user_passes_test
from django.views.decorators.http import require_GET
from datetime import datetime, time # Explicitly import datetime and time
from django.utils import timezone # Ensure timezone is imported for aware datetimes

# Import ServiceBooking and RefundRequest models
from service.models import ServiceBooking
from payments.models import RefundRequest
from payments.utils.service_refund_calc import calculate_service_refund_amount

@require_GET
@user_passes_test(lambda u: u.is_staff) # Use user_passes_test to check if user is staff
@login_required # Keep login_required to ensure user is authenticated first
def get_service_booking_details_json(request, pk):
    """
    API endpoint to return details of a specific ServiceBooking as JSON.
    Requires staff login. This endpoint also includes the latest
    refund request status associated with the booking.
    """
    try:
        # get_object_or_404 will raise Http404 if the object is not found.
        # It's best practice to catch Http404 specifically before a generic Exception.
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

        payment_date = service_booking.payment.created_at.strftime('%Y-%m-%d %H:%M') if service_booking.payment and service_booking.payment.created_at else 'N/A'
        payment_amount = float(service_booking.payment.amount) if service_booking.payment and service_booking.payment.amount is not None else 'N/A'

        motorcycle_details = {
            'year': service_booking.customer_motorcycle.year if service_booking.customer_motorcycle else 'N/A',
            'brand': service_booking.customer_motorcycle.brand if service_booking.customer_motorcycle else 'N/A',
            'model': service_booking.customer_motorcycle.model if service_booking.customer_motorcycle else 'N/A',
        }

        service_type_details = {
            'name': service_booking.service_type.name if service_booking.service_type else 'N/A',
            'description': service_booking.service_type.description if service_booking.service_type else 'N/A',
            # Ensure base_price is converted to float if not None, else 'N/A'
            'base_price': float(service_booking.service_type.base_price) if service_booking.service_type and service_booking.service_type.base_price is not None else 'N/A',
        }

        refund_status_for_booking = 'No Refund Request Yet'
        # Filter by service_booking, order by requested_at (descending) and get the first one
        latest_refund_request = RefundRequest.objects.filter(service_booking=service_booking).order_by('-requested_at').first()
        if latest_refund_request:
            # Use get_status_display() for human-readable status
            refund_status_for_booking = latest_refund_request.get_status_display()

        # Prepare snapshot for refund calculation - ensure it's a dict
        refund_policy_snapshot_for_calc = service_booking.payment.refund_policy_snapshot if service_booking.payment and service_booking.payment.refund_policy_snapshot else {}
        
        # Construct cancellation_datetime from dropoff_date and dropoff_time
        # Ensure it's timezone-aware if Django's USE_TZ is True
        cancellation_datetime = datetime.combine(service_booking.dropoff_date, service_booking.dropoff_time)
        if timezone.is_aware(timezone.now()): # Check if current timezone is aware
            cancellation_datetime = timezone.make_aware(cancellation_datetime) # Make it aware if timezone is active

        refund_calculation_results = calculate_service_refund_amount(
            service_booking=service_booking,
            cancellation_datetime=cancellation_datetime,
            refund_policy_snapshot=refund_policy_snapshot_for_calc
        )

        booking_details = {
            'id': service_booking.id, # ServiceBooking uses AutoField (integer PK)
            'service_booking_reference': service_booking.service_booking_reference,
            'customer_name': customer_name,
            'service_date': service_booking.service_date.strftime('%Y-%m-%d'),
            'dropoff_date': service_booking.dropoff_date.strftime('%Y-%m-%d'),
            'dropoff_time': service_booking.dropoff_time.strftime('%H:%M'),
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
    except Http404: # Catch Http404 specifically for 404 response
        return JsonResponse({'error': 'Service Booking not found'}, status=404)
    except Exception as e:
        # It's helpful to log the actual exception for debugging
        print(f"Error in get_service_booking_details_json: {e}")
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
