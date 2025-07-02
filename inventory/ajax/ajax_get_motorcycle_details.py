from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from inventory.models import Motorcycle


@require_GET
@login_required
def get_motorcycle_details_ajax(request, pk):

    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        motorcycle = get_object_or_404(Motorcycle, pk=pk)
    except Exception as e:

        return JsonResponse(
            {"error": f"Motorcycle not found or invalid ID: {e}"}, status=404
        )

    motorcycle_details = {
        "id": motorcycle.pk,
        "title": motorcycle.title,
        "brand": motorcycle.brand,
        "model": motorcycle.model,
        "year": motorcycle.year,
        "price": str(motorcycle.price) if motorcycle.price else None,
        "quantity": motorcycle.quantity,
        "vin_number": motorcycle.vin_number,
        "engine_number": motorcycle.engine_number,
        "condition": motorcycle.condition,
        "conditions_display": motorcycle.get_conditions_display(),
        "status": motorcycle.status,
        "is_available": motorcycle.is_available,
        "odometer": motorcycle.odometer,
        "engine_size": motorcycle.engine_size,
        "seats": motorcycle.seats,
        "transmission": motorcycle.transmission,
        "description": motorcycle.description,
        "image_url": motorcycle.image.url if motorcycle.image else None,
        "date_posted": str(motorcycle.date_posted),
        "rego": motorcycle.rego,
        "rego_exp": str(motorcycle.rego_exp) if motorcycle.rego_exp else None,
        "stock_number": motorcycle.stock_number,
    }

    return JsonResponse({"motorcycle_details": motorcycle_details})
