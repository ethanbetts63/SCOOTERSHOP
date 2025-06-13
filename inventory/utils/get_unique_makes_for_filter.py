# inventory_app/utils/make_providers.py

from inventory.utils.get_motorcycles_by_criteria import get_motorcycles_by_criteria
from django.db.models.query import QuerySet

def get_unique_makes_for_filter(
    condition_slug = None,
    year_min = None,
    year_max = None,
    engine_min_cc = None,
    engine_max_cc = None,
    price_min = None,
    price_max = None,
):
    filtered_motorcycles_queryset = get_motorcycles_by_criteria(
        condition_slug=condition_slug,
        year_min=year_min,
        year_max=year_max,
        engine_min_cc=engine_min_cc,
        engine_max_cc=engine_max_cc,
        price_min=price_min,
        price_max=price_max,
    )

    unique_makes = filtered_motorcycles_queryset.values_list('brand', flat=True).distinct()

    return sorted(list(unique_makes))
