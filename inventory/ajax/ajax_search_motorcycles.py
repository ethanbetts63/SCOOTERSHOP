# inventory/ajax/ajax_search_motorcycles.py

from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from inventory.models import Motorcycle

@require_GET
@login_required
def search_motorcycles_ajax(request):
    """
    AJAX endpoint to search for Motorcycle instances for sales bookings.
    Searches across title, brand, model, VIN, stock number, ID (PK), and registration.
    By default, it shows available or reserved motorcycles.
    Returns a JSON response with a list of matching motorcycles.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    search_term = request.GET.get('query', '').strip()
    include_unavailable = request.GET.get('include_unavailable', 'false').lower() == 'true'

    motorcycles_data = []

    if search_term:
        search_query = (
            Q(pk__icontains=search_term) |
            Q(title__icontains=search_term) |
            Q(brand__icontains=search_term) |
            Q(model__icontains=search_term) |
            Q(vin_number__icontains=search_term) |
            Q(stock_number__icontains=search_term) |
            Q(rego__icontains=search_term)
        )

        queryset = Motorcycle.objects.filter(search_query)

        if not include_unavailable:
            # FIX: The filter logic is now more precise. It correctly includes only
            # motorcycles with a status of 'for_sale' or 'reserved'.
            queryset = queryset.filter(status__in=['for_sale', 'reserved'])
        
        queryset = queryset.distinct().order_by('brand', 'model', 'year')

        for motorcycle in queryset[:20]:
            motorcycles_data.append({
                'id': motorcycle.pk,
                'title': motorcycle.title,
                'brand': motorcycle.brand,
                'model': motorcycle.model,
                'year': motorcycle.year,
                'status': motorcycle.get_status_display(), # Use display name for clarity
                'is_available': motorcycle.is_available,
                'quantity': motorcycle.quantity,
                'condition': motorcycle.get_condition_display(), # Use display name
                'price': str(motorcycle.price) if motorcycle.price else None,
                'rego': motorcycle.rego,
                'stock_number': motorcycle.stock_number,
            })

    return JsonResponse({'motorcycles': motorcycles_data})
