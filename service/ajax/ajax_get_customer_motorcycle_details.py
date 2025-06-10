
from django.http import JsonResponse
from service.models import ServiceProfile, CustomerMotorcycle # Ensure these are imported
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET


@require_GET
def get_motorcycle_details_ajax(request, motorcycle_id):
    """
    AJAX endpoint to retrieve detailed information for a specific CustomerMotorcycle.
    Returns a JSON response with all fields necessary to populate the CustomerMotorcycleForm.
    """
    try:
        motorcycle = get_object_or_404(CustomerMotorcycle, pk=motorcycle_id)
    except Exception as e:
        return JsonResponse({'error': f'Motorcycle not found or invalid ID: {e}'}, status=404)

    # Serialize all relevant fields from the CustomerMotorcycle instance
    # This should match the fields expected by your CustomerMotorcycleForm
    motorcycle_details = {
        'id': motorcycle.pk,
        'brand': motorcycle.brand,
        'model': motorcycle.model,
        'year': motorcycle.year,
        'engine_size': motorcycle.engine_size,
        'rego': motorcycle.rego,
        'vin_number': motorcycle.vin_number,
        'odometer': motorcycle.odometer,
        'transmission': motorcycle.transmission,
        'engine_number': motorcycle.engine_number,
    }

    return JsonResponse({'motorcycle_details': motorcycle_details})

