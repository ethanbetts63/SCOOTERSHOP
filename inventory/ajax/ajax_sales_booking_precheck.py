# inventory/ajax/ajax_get_motorcycle_details.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from inventory.models import Motorcycle # Import the Motorcycle model

@require_GET
@login_required
def get_motorcycle_details_ajax(request, pk):
    """
    AJAX endpoint to retrieve detailed information for a specific Motorcycle.
    Returns a JSON response with all fields necessary to populate the motorcycle display area
    in the admin sales booking form.
    """
    # Ensure only staff members can access this endpoint
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        motorcycle = get_object_or_404(Motorcycle, pk=pk)
    except Exception as e:
        # Return a 404 error if the motorcycle is not found
        return JsonResponse({'error': f'Motorcycle not found or invalid ID: {e}'}, status=404)

    # Serialize all relevant fields from the Motorcycle instance
    # This should include all fields you might want to display for the selected motorcycle
    motorcycle_details = {
        'id': motorcycle.pk,
        'title': motorcycle.title,
        'brand': motorcycle.brand,
        'model': motorcycle.model,
        'year': motorcycle.year,
        'price': str(motorcycle.price) if motorcycle.price else None, # Convert Decimal to string
        'quantity': motorcycle.quantity,
        'vin_number': motorcycle.vin_number,
        'engine_number': motorcycle.engine_number,
        'condition': motorcycle.condition, # 'new', 'used', 'demo', 'hire'
        'conditions_display': motorcycle.get_conditions_display(), # Display string for conditions
        'status': motorcycle.status, # Current sales/hire status
        'is_available': motorcycle.is_available, # Boolean availability flag
        'odometer': motorcycle.odometer,
        'engine_size': motorcycle.engine_size,
        'seats': motorcycle.seats,
        'transmission': motorcycle.transmission,
        'description': motorcycle.description,
        'image_url': motorcycle.image.url if motorcycle.image else None, # URL for motorcycle image
        'date_posted': str(motorcycle.date_posted), # Convert datetime to string
        'rego': motorcycle.rego,
        'rego_exp': str(motorcycle.rego_exp) if motorcycle.rego_exp else None, # Convert date to string
        'stock_number': motorcycle.stock_number,
        'daily_hire_rate': str(motorcycle.daily_hire_rate) if motorcycle.daily_hire_rate else None,
        'hourly_hire_rate': str(motorcycle.hourly_hire_rate) if motorcycle.hourly_hire_rate else None,
    }

    return JsonResponse({'motorcycle_details': motorcycle_details})

