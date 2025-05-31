# payments/views/HireRefunds/utils.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from hire.models import HireBooking
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
import json

@require_GET
@login_required
def get_hire_booking_details_json(request, pk):
    """
    API endpoint to return details of a specific HireBooking as JSON.
    Requires staff login.
    """
    try:
        hire_booking = get_object_or_404(HireBooking, pk=pk)

        # Basic details of the chosen hire booking
        booking_details = {
            'id': hire_booking.id,
            'booking_reference': hire_booking.booking_reference,
            'customer_name': hire_booking.driver_profile.user.get_full_name() if hire_booking.driver_profile and hire_booking.driver_profile.user else (hire_booking.driver_profile.full_name if hire_booking.driver_profile else 'N/A'),
            'pickup_date': hire_booking.pickup_date.strftime('%Y-%m-%d') if hire_booking.pickup_date else 'N/A',
            'pickup_time': hire_booking.pickup_time.strftime('%H:%M') if hire_booking.pickup_time else 'N/A',
            'return_date': hire_booking.return_date.strftime('%Y-%m-%d') if hire_booking.return_date else 'N/A',
            'return_time': hire_booking.return_time.strftime('%H:%M') if hire_booking.return_time else 'N/A',
            'motorcycle_year': hire_booking.motorcycle.year if hire_booking.motorcycle else 'N/A',
            'motorcycle_brand': hire_booking.motorcycle.brand.name if hire_booking.motorcycle and hire_booking.motorcycle.brand else 'N/A',
            'motorcycle_model': hire_booking.motorcycle.model if hire_booking.motorcycle else 'N/A',
            'payment_method': hire_booking.get_payment_method_display() if hire_booking.payment_method else 'N/A',
            'payment_date': hire_booking.payment.created_at.strftime('%Y-%m-%d %H:%M') if hire_booking.payment and hire_booking.payment.created_at else 'N/A',
            'payment_amount': float(hire_booking.payment.amount) if hire_booking.payment and hire_booking.payment.amount else 'N/A',
            'booking_status': hire_booking.get_status_display(),
            'payment_status': hire_booking.get_payment_status_display(),
            # Add any other details you might need
        }
        return JsonResponse(booking_details)
    except HireBooking.DoesNotExist:
        return JsonResponse({'error': 'Hire Booking not found'}, status=404)
    except Exception as e:
        # Log the exception for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error fetching hire booking details for PK {pk}")
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

