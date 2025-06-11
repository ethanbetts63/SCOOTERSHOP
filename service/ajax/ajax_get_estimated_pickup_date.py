# service/ajax/ajax_get_estimated_pickup_date.py

from django.http import JsonResponse
from django.views.decorators.http import require_GET
# Changed get_object_or_404 to models import for ServiceType.objects.get
from service.models import ServiceType 
import datetime

from service.utils.calculate_estimated_pickup_date import calculate_estimated_pickup_date

@require_GET
def get_estimated_pickup_date_ajax(request):
    """
    AJAX endpoint to calculate the estimated pickup date based on service type
    and service date provided via GET parameters.

    Expected GET parameters:
    - service_type_id (int): The ID of the selected ServiceType.
    - service_date (str): The chosen service date in 'YYYY-MM-DD' format.
    """
    service_type_id = request.GET.get('service_type_id')
    service_date_str = request.GET.get('service_date')

    # Basic validation for missing parameters
    if not service_type_id or not service_date_str:
        return JsonResponse({'error': 'Missing service_type_id or service_date'}, status=400)

    try:
        # Changed from get_object_or_404 to ServiceType.objects.get()
        service_type = ServiceType.objects.get(pk=service_type_id) 
        service_date = datetime.datetime.strptime(service_date_str, '%Y-%m-%d').date()
    except ServiceType.DoesNotExist:
        # This will now correctly catch if ServiceType is not found
        return JsonResponse({'error': 'ServiceType not found'}, status=404)
    except ValueError:
        # Corrected expected date format string
        return JsonResponse({'error': 'Invalid date format. ExpectedYYYY-MM-DD.'}, status=400)
    except Exception as e:
        # Generic error handler for unexpected issues
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

    # Create a mock object that mimics a booking instance for the utility function.
    # This avoids creating a real TempServiceBooking or ServiceBooking in the DB
    # just for a calculation, which is more efficient for an AJAX call.
    class MockBookingInstance:
        def __init__(self, service_type, service_date):
            self.service_type = service_type
            self.service_date = service_date
            self.estimated_pickup_date = None # Will be set by the utility
        
        def save(self, update_fields=None):
            pass # Do nothing, as this is a mock object

    mock_booking = MockBookingInstance(service_type, service_date)

    # Use the shared utility function to calculate the estimated pickup date
    calculated_date = calculate_estimated_pickup_date(mock_booking)

    if calculated_date:
        return JsonResponse({
            'estimated_pickup_date': calculated_date.strftime('%Y-%m-%d')
        })
    else:
        # Changed status to 500 when calculation fails unexpectedly
        return JsonResponse({'error': 'Could not calculate estimated pickup date'}, status=500)

