                                                

from django.db.models import Q
from inventory.models import Motorcycle, MotorcycleCondition                                         

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

                                                           
    if condition_slug == 'new':
        queryset = queryset.filter(conditions__name='new')
    elif condition_slug == 'used':
                                                                           
        queryset = queryset.filter(
            Q(conditions__name='used') | Q(conditions__name='demo')
        )
    elif condition_slug and condition_slug != 'all':
                                               
        queryset = queryset.filter(conditions__name=condition_slug)

                                                  
                                                                        
    unique_makes = queryset.values_list('brand', flat=True).distinct()

                                                                
    return set(unique_makes)

