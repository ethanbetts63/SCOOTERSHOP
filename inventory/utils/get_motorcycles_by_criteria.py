# inventory/utils/get_motorcycles_by_criteria.py

from django.db.models import Q # Import Q object for complex lookups
from inventory.models import Motorcycle, MotorcycleCondition

def get_motorcycles_by_criteria(condition_slug=None, brand=None, model=None, year_min=None, year_max=None, price_min=None, price_max=None, engine_min_cc=None, engine_max_cc=None, order=None):
    """
    Retrieves a queryset of motorcycles based on various filtering criteria.

    Args:
        condition_slug (str, optional): A slug representing the condition ('new', 'used', 'all').
                                       'used' will include both 'used' and 'demo' motorcycles.
        brand (str, optional): Filters by the brand of the motorcycle.
        model (str, optional): Filters by a keyword in the motorcycle's model name (case-insensitive).
        year_min (int, optional): Filters for motorcycles manufactured in or after this year.
        year_max (int, optional): Filters for motorcycles manufactured in or before this year.
        price_min (Decimal, optional): Filters for motorcycles with a price greater than or equal to this value.
        price_max (Decimal, optional): Filters for motorcycles with a price less than or equal to this value.
        engine_min_cc (int, optional): Filters for motorcycles with an engine size greater than or equal to this value.
        engine_max_cc (int, optional): Filters for motorcycles with an engine size less than or equal to this value.
        order (str, optional): Specifies the ordering of the results.
                                e.g., 'price_low_to_high', 'price_high_to_low',
                                'age_new_to_old', 'age_old_to_new'.

    Returns:
        django.db.models.QuerySet: A filtered and ordered queryset of Motorcycle objects.
    """
    queryset = Motorcycle.objects.all()

    # Apply condition filtering based on the slug
    if condition_slug == 'new':
        # Filter for motorcycles explicitly marked as 'new' condition
        queryset = queryset.filter(conditions__name='new').distinct()
    elif condition_slug == 'used':
        # For 'used' motorcycles, include both 'used' and 'demo' conditions
        # Use Q objects for OR logic in filters
        queryset = queryset.filter(
            Q(conditions__name='used') | Q(conditions__name='demo')
        ).distinct()
    elif condition_slug and condition_slug != 'all':
        # For any other specific condition slug
        queryset = queryset.filter(conditions__name=condition_slug).distinct()

    # Apply other filters
    if brand:
        queryset = queryset.filter(brand=brand)
    if model:
        queryset = queryset.filter(model__icontains=model) # Case-insensitive contains

    if year_min:
        queryset = queryset.filter(year__gte=year_min)
    if year_max:
        queryset = queryset.filter(year__lte=year_max)

    if price_min is not None:
        queryset = queryset.filter(price__gte=price_min)
    if price_max is not None:
        queryset = queryset.filter(price__lte=price_max)

    # --- NEW: Apply engine size filters ---
    if engine_min_cc is not None:
        queryset = queryset.filter(engine_size__gte=engine_min_cc)
    if engine_max_cc is not None:
        queryset = queryset.filter(engine_size__lte=engine_max_cc)
    # --- END NEW ---

    # Apply ordering
    if order == 'price_low_to_high':
        queryset = queryset.order_by('price')
    elif order == 'price_high_to_low':
        queryset = queryset.order_by('-price')
    elif order == 'age_new_to_old':
        queryset = queryset.order_by('-year', '-date_posted') # Order by year descending, then date posted descending
    elif order == 'age_old_to_new':
        queryset = queryset.order_by('year', 'date_posted') # Order by year ascending, then date posted ascending
    else:
        # Default ordering if none specified or invalid
        queryset = queryset.order_by('-date_posted')

    return queryset

