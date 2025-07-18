from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from ..decorators import admin_required
from inventory.models import Motorcycle


@require_GET
@admin_required
def search_motorcycles_ajax(request):
    """
    Handles AJAX requests to search for motorcycles based on a query and
    optional filters like condition.
    """
    search_term = request.GET.get("query", "").strip()
    condition = request.GET.get("condition")
    motorcycles_data = []

    motorcycles_data = []

    if search_term:
        # Base search query across multiple fields
        search_query = (
            Q(pk__icontains=search_term)
            | Q(title__icontains=search_term)
            | Q(brand__icontains=search_term)
            | Q(model__icontains=search_term)
            | Q(vin_number__icontains=search_term)
            | Q(stock_number__icontains=search_term)
            | Q(rego__icontains=search_term)
        )
        queryset = Motorcycle.objects.filter(search_query)

        # Apply condition filter, checking both the simple and M2M fields
        if condition in ["new", "used", "demo"]:
            condition_filter = Q(condition=condition) | Q(
                conditions__name__iexact=condition
            )
            queryset = queryset.filter(condition_filter)

        # Order and limit the results
        queryset = queryset.distinct().order_by("brand", "model", "year")[:20]

        for motorcycle in queryset:
            motorcycles_data.append(
                {
                    "id": motorcycle.pk,
                    "title": motorcycle.title,
                    "brand": motorcycle.brand,
                    "model": motorcycle.model,
                    "year": motorcycle.year,
                    "status": motorcycle.get_status_display(),
                    "is_available": motorcycle.is_available,
                    "quantity": motorcycle.quantity,
                    "condition": motorcycle.get_conditions_display(),
                    "price": str(motorcycle.price) if motorcycle.price else None,
                    "rego": motorcycle.rego,
                    "stock_number": motorcycle.stock_number,
                }
            )

    return JsonResponse({"motorcycles": motorcycles_data})
