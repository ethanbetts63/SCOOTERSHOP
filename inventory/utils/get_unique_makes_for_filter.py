# inventory/utils/get_unique_makes_for_filter.py

from django.db.models import Q
from inventory.models import Motorcycle, MotorcycleCondition # Ensure MotorcycleCondition is imported

def get_unique_makes_for_filter(condition_slug=None):
    """
    Retrieves a set of unique motorcycle brands relevant to a given condition slug.
    This is used to populate the 'Brand' filter dropdown dynamically.

    Args:
        condition_slug (str, optional): The condition slug ('new', 'used', 'all').
                                       'used' will retrieve brands from both 'used' and 'demo' motorcycles.

    Returns:
        set: A set of unique brand names (strings).
    """
    queryset = Motorcycle.objects.all()

    # Apply condition filtering before getting unique makes
    if condition_slug == 'new':
        queryset = queryset.filter(conditions__name='new')
    elif condition_slug == 'used':
        # For 'used' conditions, include both 'used' and 'demo' motorcycles
        queryset = queryset.filter(
            Q(conditions__name='used') | Q(conditions__name='demo')
        )
    elif condition_slug and condition_slug != 'all':
        # For any other specific condition slug
        queryset = queryset.filter(conditions__name=condition_slug)

    # Get unique brands from the filtered queryset
    # .distinct() is important when using M2M fields to avoid duplicates
    unique_makes = queryset.values_list('brand', flat=True).distinct()

    # Return as a set for quick lookups and to ensure uniqueness
    return set(unique_makes)

