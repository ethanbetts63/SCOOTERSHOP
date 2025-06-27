from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from inventory.models import TempSalesBooking, Motorcycle
from django.db import transaction

@csrf_exempt
@require_POST
def check_motorcycle_availability(request):
    """
    AJAX endpoint to check if a motorcycle associated with a temporary sales booking
    is still available. This is a real-time check intended to reduce the chance
    of a user attempting to pay for an already reserved or sold motorcycle.
    """
    try:
        # Load the request body as JSON
        data = json.loads(request.body)
        temp_booking_uuid = data.get('temp_booking_uuid')

        # Validate that temp_booking_uuid is provided
        if not temp_booking_uuid:
            return JsonResponse({'available': False, 'message': 'Temporary booking ID is required.'}, status=400)

        # Use a transaction with select_for_update for a strong consistency check.
        # This will lock the motorcycle row, preventing another transaction from modifying
        # its availability status until this transaction is complete.
        with transaction.atomic():
            # Retrieve the temporary booking
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)

            # Retrieve the motorcycle associated with the temporary booking,
            # using select_for_update to lock the row.
            motorcycle = get_object_or_404(
                Motorcycle.objects.select_for_update(),
                pk=temp_booking.motorcycle.pk
            )

            # Check the motorcycle's availability
            if not motorcycle.is_available:
                return JsonResponse({'available': False, 'message': 'Sorry, this motorcycle has just been reserved or sold.'})
            
            # If the motorcycle is available, return success
            return JsonResponse({'available': True, 'message': 'Motorcycle is available.'})

    except TempSalesBooking.DoesNotExist:
        return JsonResponse({'available': False, 'message': 'Temporary booking not found.'}, status=404)
    except Motorcycle.DoesNotExist:
        return JsonResponse({'available': False, 'message': 'Associated motorcycle not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'available': False, 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        # Catch any other unexpected errors
        return JsonResponse({'available': False, 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
