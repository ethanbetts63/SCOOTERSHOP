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
    # Ensure only staff members can access this endpoint
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    search_term = request.GET.get('query', '').strip()
    # An optional parameter to include unavailable motorcycles in the search results
    include_unavailable = request.GET.get('include_unavailable', 'false').lower() == 'true'

    motorcycles_data = []

    if search_term:
        # Define base query filters.
        # Q objects allow for complex OR conditions.
        search_query = (
            Q(pk__icontains=search_term) | # Added: Search by Motorcycle ID (PK)
            Q(title__icontains=search_term) |
            Q(brand__icontains=search_term) |
            Q(model__icontains=search_term) |
            Q(vin_number__icontains=search_term) |
            Q(stock_number__icontains=search_term) |
            Q(rego__icontains=search_term) # Added: Search by Registration number
        )

        # Start with all motorcycles, then apply availability filters if not including unavailable
        queryset = Motorcycle.objects.filter(search_query)

        if not include_unavailable:
            # Filter for motorcycles that are explicitly 'for_sale' or 'reserved'.
            # 'sold' and 'unavailable' should generally not appear in regular search for booking.
            # However, 'reserved' bikes can still be viewed in admin to manage existing bookings.
            queryset = queryset.filter(Q(is_available=True) | Q(status='reserved'))
        
        # Ensure distinct results and order for consistent display
        queryset = queryset.distinct().order_by('brand', 'model', 'year')

        # Limit results to prevent overwhelming the client
        for motorcycle in queryset[:20]: # Limit to top 20 results
            motorcycles_data.append({
                'id': motorcycle.pk,
                'title': motorcycle.title,
                'brand': motorcycle.brand,
                'model': motorcycle.model,
                'year': motorcycle.year,
                'status': motorcycle.status,
                'is_available': motorcycle.is_available,
                'quantity': motorcycle.quantity,
                'condition': motorcycle.condition, # 'new', 'used', 'demo', 'hire'
                'price': str(motorcycle.price) if motorcycle.price else None, # Convert Decimal to string
                'rego': motorcycle.rego,
                'stock_number': motorcycle.stock_number,
                # Include other relevant fields for quick display in search results
            })

    return JsonResponse({'motorcycles': motorcycles_data})

