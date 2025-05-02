# core/views/utils.py

from ..models import Motorcycle # Import models
from django.db.models.fields import DecimalField, IntegerField # Needed for checking field types

def get_featured_motorcycles(exclude_id=None, limit=3, condition=None):
    """
    Retrieves a limited number of available motorcycles, optionally excluding one
    and filtering by a specific condition name.
    """
    queryset = Motorcycle.objects.filter(is_available=True)

    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)

    # Apply condition filter case-insensitively using the ManyToManyField
    if condition:
        condition_lower = condition.lower()

        # Handle the demo case - show used bikes for demo condition
        if condition_lower == 'demo':
            queryset = queryset.filter(conditions__name__iexact='used')
        # Normal case - filter by the actual condition name in the ManyToManyField
        elif condition_lower in ['new', 'used', 'hire']:
             queryset = queryset.filter(conditions__name__iexact=condition_lower)
        # Ensure uniqueness if a motorcycle has multiple conditions that match
        queryset = queryset.distinct()


    # Order randomly and get the limit
    # .order_by('?') can be slow on large datasets, consider alternatives if performance is an issue
    results = list(queryset.order_by('?')[:limit])

    return results

# You can add other utility functions here as needed