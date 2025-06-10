# service/ajax_views.py

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
import datetime
import json

# Import your existing utility function
from ..utils import get_service_date_availability # Assuming get_service_date_availability.py is in service/utils.py

# Ensure models are imported if your get_service_date_availability directly uses them
# from service.models import ServiceSettings, BlockedServiceDate, ServiceBooking

@require_GET
def get_service_date_availability_ajax(request):
    """
    AJAX endpoint to provide service date availability information for Flatpickr.
    Leverages the existing get_service_date_availability utility.
    Returns JSON with min_date and disabled_dates (as a list, not a string).
    """
    try:
        min_date, disabled_dates_json = get_service_date_availability()

        # Parse the JSON string back into a Python list/dict for direct inclusion in JsonResponse
        # This is because JsonResponse will automatically serialize Python objects to JSON,
        # so we don't want a JSON string *inside* another JSON string.
        disabled_dates = json.loads(disabled_dates_json)

        response_data = {
            'min_date': min_date.strftime('%Y-%m-%d'), # Format date to string for JS
            'disabled_dates': disabled_dates,
            'warnings': [] # Initialize warnings list
        }

        # Add any specific admin-facing warnings if necessary,
        # though the disabled_dates should handle most of this.
        # For instance, if you wanted to explicitly flag certain capacities.

        return JsonResponse(response_data)

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_service_date_availability_ajax: {e}")
        return JsonResponse({'error': 'Could not retrieve service date availability.'}, status=500)

