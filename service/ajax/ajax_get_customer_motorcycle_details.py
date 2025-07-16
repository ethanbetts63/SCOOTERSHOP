from django.http import JsonResponse
from service.models import CustomerMotorcycle
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from ..decorators import admin_required


@require_GET
def get_motorcycle_details_ajax(request, motorcycle_id):

    try:
        motorcycle = get_object_or_404(CustomerMotorcycle, pk=motorcycle_id)
    except Exception as e:
        return JsonResponse(
            {"error": f"Motorcycle not found or invalid ID: {e}"}, status=404
        )

    motorcycle_details = {
        "id": motorcycle.pk,
        "brand": motorcycle.brand,
        "model": motorcycle.model,
        "year": motorcycle.year,
        "engine_size": motorcycle.engine_size,
        "rego": motorcycle.rego,
        "vin_number": motorcycle.vin_number,
        "odometer": motorcycle.odometer,
        "transmission": motorcycle.transmission,
        "engine_number": motorcycle.engine_number,
    }

    return JsonResponse({"motorcycle_details": motorcycle_details})
