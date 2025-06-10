# service/views.py

from django.http import JsonResponse
from service.models import ServiceProfile, CustomerMotorcycle # Ensure these are imported
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET


@require_GET
def get_customer_motorcycles_ajax(request, profile_id):
    """
    AJAX endpoint to retrieve a list of motorcycles associated with a given ServiceProfile.
    Returns a JSON response containing motorcycle IDs, brands, models, and registration numbers.
    """
    try:
        # Ensure the ServiceProfile exists
        service_profile = get_object_or_404(ServiceProfile, pk=profile_id)
    except Exception as e:
        # Return a 404 or a more specific error if the profile is not found or invalid
        return JsonResponse({'error': f'ServiceProfile not found or invalid ID: {e}'}, status=404)

    # Fetch motorcycles related to this service profile
    # Order by brand and model for consistent display
    motorcycles = CustomerMotorcycle.objects.filter(service_profile=service_profile).order_by('brand', 'model')

    # Prepare data for JSON response
    motorcycle_data = []
    for mc in motorcycles:
        motorcycle_data.append({
            'id': mc.pk,
            'brand': mc.brand,
            'model': mc.model,
            'year': mc.year, # Include year for better identification
            'rego': mc.rego,
            # Add any other fields you want to display or use in the frontend
        })

    return JsonResponse({'motorcycles': motorcycle_data})
